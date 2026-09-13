from datetime import timedelta
from odoo import models, fields, api


class ChurchBulkMessage(models.Model):
    _name = 'church.bulk.message'
    _description = 'Bulk Message to a Member Segment'
    _order = 'create_date desc'

    title = fields.Char(string='Title', required=True)
    message = fields.Text(string='Message', required=True)
    segment_type = fields.Selection([
        ('all', 'All Members'),
        ('cell_group', 'A Cell Group'),
        ('inactive', 'Inactive Members'),
        ('birthday_today', "Today's Birthdays"),
        ('pledge_overdue', 'Overdue Pledges'),
    ], string='Segment', required=True, default='all')
    cell_group_id = fields.Many2one('cell.group', string='Cell Group')
    inactive_days = fields.Integer(string='Inactive For (days)', default=30)

    sent_at = fields.Datetime(string='Sent At', readonly=True)
    sent_by_id = fields.Many2one('hr.employee', string='Sent By', readonly=True)
    recipient_count = fields.Integer(string='Recipients', readonly=True)
    notification_id = fields.Many2one('revive.notification', string='Notification Record', readonly=True)

    def _resolve_recipients(self):
        self.ensure_one()
        ResPartner = self.env['res.partner'].sudo()
        if self.segment_type == 'all':
            return ResPartner.search([('is_member', '=', True)])
        if self.segment_type == 'cell_group':
            if not self.cell_group_id:
                return ResPartner.browse()
            return self.cell_group_id.member_ids
        if self.segment_type == 'inactive':
            cutoff = fields.Datetime.now() - timedelta(days=self.inactive_days or 30)
            active_ids = self.env['church.event.attendance'].sudo().search([
                ('check_in_time', '>=', cutoff),
            ]).mapped('member_id').ids
            return ResPartner.search([
                ('is_member', '=', True), ('id', 'not in', active_ids or [0]),
            ])
        if self.segment_type == 'birthday_today':
            today = fields.Date.context_today(self)
            members = ResPartner.search([
                ('is_member', '=', True), ('date_of_birth', '!=', False),
            ])
            return members.filtered(
                lambda m: m.date_of_birth.month == today.month and m.date_of_birth.day == today.day
            )
        if self.segment_type == 'pledge_overdue':
            today = fields.Date.context_today(self)
            pledges = self.env['church.give.pledge'].sudo().search([
                ('status', '=', 'active'), ('next_reminder_date', '!=', False),
                ('next_reminder_date', '<=', today),
            ])
            return pledges.mapped('member_id')
        return ResPartner.browse()

    def action_send(self):
        Notification = self.env['revive.notification'].sudo()
        for msg in self:
            recipients = msg._resolve_recipients()

            if msg.segment_type == 'all':
                # Reuse the existing FCM broadcast path (and its own
                # status/sent_at bookkeeping) for the "everyone" case.
                notif = Notification.create({
                    'title': msg.title, 'message': msg.message, 'target': 'all',
                })
                try:
                    notif.action_send()
                except Exception:
                    pass  # FCM misconfiguration shouldn't block the in-app notification below
            else:
                notif = Notification.create({
                    'title': msg.title, 'message': msg.message, 'target': 'all',
                    'status': 'sent', 'sent_at': fields.Datetime.now(),
                    'target_member_ids': [(6, 0, recipients.ids)],
                })

            msg.write({
                'sent_at': fields.Datetime.now(),
                'recipient_count': len(recipients),
                'notification_id': notif.id,
            })

    # ── Church Management RPC (Phase 4) ─────────────────────────

    def _sender_ok(self, requester_staff_id):
        if not requester_staff_id:
            return False
        employee = self.env['hr.employee'].sudo().browse(requester_staff_id)
        return employee.exists() and employee.staff_role in ('admin', 'pastor')

    @api.model
    def app_send_bulk_message(self, vals, requester_staff_id):
        if not self._sender_ok(requester_staff_id):
            return {'success': False, 'error': 'Not authorized'}
        employee = self.env['hr.employee'].sudo().browse(requester_staff_id)
        vals = dict(vals or {})
        msg = self.sudo().create(vals)
        msg.sent_by_id = employee.id
        msg.action_send()
        return {'success': True, 'message_id': msg.id, 'recipient_count': msg.recipient_count}

    @api.model
    def app_get_bulk_messages(self, requester_staff_id):
        if not self._sender_ok(requester_staff_id):
            return {'success': False, 'error': 'Not authorized'}
        messages = self.sudo().search([], order='create_date desc', limit=50)
        return {'success': True, 'messages': [{
            'id': m.id, 'title': m.title, 'segment_type': m.segment_type,
            'recipient_count': m.recipient_count,
            'sent_at': m.sent_at.isoformat() if m.sent_at else '',
        } for m in messages]}
