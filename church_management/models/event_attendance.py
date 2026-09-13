from odoo import models, fields, api


class ChurchEventAttendance(models.Model):
    _name = 'church.event.attendance'
    _description = 'Event Attendance / Check-in'
    _order = 'check_in_time desc'

    # Targets onevoice.event (from the onevoice27 dependency) — that model
    # is what actually powers the app's general "Events" page today (see
    # OdooService.fetchEvents / events_page.dart), even though its name
    # suggests OneVoice27-only. church.event (in volunteer_and_donation_
    # management) appears superseded by it.
    event_id = fields.Many2one('onevoice.event', string='Event', required=True)
    member_id = fields.Many2one(
        'res.partner', string='Member', required=True,
        domain=[('is_member', '=', True)],
    )
    check_in_time = fields.Datetime(string='Checked In At', default=fields.Datetime.now, required=True)
    checked_in_by_staff_id = fields.Many2one(
        'hr.employee', string='Checked In By',
        help='Left blank for self check-in.',
    )
    method = fields.Selection([
        ('manual', 'Manual'), ('qr', 'QR Code'),
        ('kiosk', 'Kiosk'), ('self', 'Self Check-in'),
    ], string='Method', default='manual', required=True)

    _sql_constraints = [
        ('event_member_uniq', 'unique(event_id, member_id)',
         'This member is already checked in to this event.'),
    ]

    # ── Church Management RPC (Phase 2) ─────────────────────────

    @api.model
    def app_check_in(self, event_id, member_id, requester_partner_id=None, requester_staff_id=None):
        ResPartner = self.env['res.partner']
        mode, scope = ResPartner._church_caller_scope(requester_partner_id, requester_staff_id)
        if mode == 'denied':
            return {'success': False, 'error': 'Not authorized'}

        # A plain member may only self check-in.
        if mode == 'self' and member_id != scope:
            return {'success': False, 'error': 'You can only check yourself in'}

        existing = self.sudo().search([
            ('event_id', '=', event_id), ('member_id', '=', member_id),
        ], limit=1)
        if existing:
            return {'success': True, 'attendance_id': existing.id, 'already_checked_in': True}

        record = self.sudo().create({
            'event_id': event_id,
            'member_id': member_id,
            'method': 'self' if mode == 'self' else 'manual',
            'checked_in_by_staff_id': requester_staff_id or False,
        })
        return {'success': True, 'attendance_id': record.id, 'already_checked_in': False}

    @api.model
    def app_get_event_attendance(self, event_id, requester_staff_id=None):
        mode, _scope = self.env['res.partner']._church_caller_scope(requester_staff_id=requester_staff_id)
        if mode not in ('all', 'assigned'):
            return {'success': False, 'error': 'Not authorized'}

        records = self.sudo().search([('event_id', '=', event_id)], order='check_in_time desc')
        return {'success': True, 'attendance': records.read([
            'id', 'member_id', 'check_in_time', 'method',
        ])}

    @api.model
    def app_get_my_attendance(self, requester_partner_id):
        mode, scope = self.env['res.partner']._church_caller_scope(requester_partner_id=requester_partner_id)
        if mode != 'self':
            return {'success': False, 'error': 'Not authorized'}

        records = self.sudo().search([('member_id', '=', scope)], order='check_in_time desc', limit=100)
        return {'success': True, 'attendance': records.read([
            'id', 'event_id', 'check_in_time', 'method',
        ])}
