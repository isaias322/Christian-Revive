from odoo import models, fields, api


class CellGroup(models.Model):
    _name = 'cell.group'
    _description = 'Cell / Small Group'
    _order = 'name'

    name = fields.Char(string='Group Name', required=True)
    zone = fields.Char(string='Zone')
    district = fields.Char(string='District')

    leader_id = fields.Many2one(
        'res.partner', string='Leader', required=True,
        domain=[('is_member', '=', True)],
    )
    member_ids = fields.Many2many(
        'res.partner', string='Roster',
        domain=[('is_member', '=', True)],
    )
    member_count = fields.Integer(string='Members', compute='_compute_member_count')

    meeting_day = fields.Selection([
        ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], string='Meeting Day')
    meeting_time = fields.Char(string='Meeting Time', help='e.g. "6:00 PM"')
    meeting_location = fields.Char(string='Meeting Location')

    @api.depends('member_ids')
    def _compute_member_count(self):
        for group in self:
            group.member_count = len(group.member_ids)

    # ── Church Management RPC (Phase 2) ─────────────────────────

    def _is_leader_of(self, partner_id):
        return bool(self.sudo().search_count([
            ('id', '=', self.id), ('leader_id', '=', partner_id),
        ]))

    @api.model
    def app_get_cell_groups(self, requester_partner_id=None, requester_staff_id=None):
        ResPartner = self.env['res.partner']
        mode, scope = ResPartner._church_caller_scope(requester_partner_id, requester_staff_id)
        if mode == 'denied':
            return {'success': False, 'error': 'Not authorized'}

        if mode == 'all':
            groups = self.sudo().search([], order='name')
        elif mode == 'assigned':
            # Associate pastor: groups whose leader is one of their assigned members,
            # or that contain any of their assigned members.
            scope_ids = scope or []
            groups = self.sudo().search([
                '|', ('leader_id', 'in', scope_ids), ('member_ids', 'in', scope_ids),
            ], order='name')
        else:  # 'self' — a plain member: groups they lead or belong to
            partner_id = scope
            groups = self.sudo().search([
                '|', ('leader_id', '=', partner_id), ('member_ids', '=', partner_id),
            ], order='name')

        return {'success': True, 'groups': groups.read([
            'id', 'name', 'zone', 'district', 'leader_id',
            'member_count', 'meeting_day', 'meeting_time', 'meeting_location',
        ])}

    @api.model
    def app_get_cell_group_detail(self, group_id, requester_partner_id=None, requester_staff_id=None):
        ResPartner = self.env['res.partner']
        mode, scope = ResPartner._church_caller_scope(requester_partner_id, requester_staff_id)
        if mode == 'denied':
            return {'success': False, 'error': 'Not authorized'}

        group = self.sudo().browse(group_id)
        if not group.exists():
            return {'success': False, 'error': 'Group not found'}

        if mode == 'assigned' and not (
            group.leader_id.id in (scope or []) or
            any(m.id in (scope or []) for m in group.member_ids)
        ):
            return {'success': False, 'error': 'Not authorized for this group'}
        if mode == 'self' and group.leader_id.id != scope and scope not in group.member_ids.ids:
            return {'success': False, 'error': 'Not authorized for this group'}

        data = group.read([
            'id', 'name', 'zone', 'district', 'leader_id',
            'meeting_day', 'meeting_time', 'meeting_location',
        ])[0]
        data['members'] = group.member_ids.read(['id', 'name', 'membership_status'])
        return {'success': True, 'group': data}

    @api.model
    def app_create_cell_group(self, vals, requester_staff_id=None):
        mode, _scope = self.env['res.partner']._church_caller_scope(requester_staff_id=requester_staff_id)
        if mode not in ('all', 'assigned'):
            return {'success': False, 'error': 'Not authorized to create groups'}
        group = self.sudo().create(vals or {})
        return {'success': True, 'group_id': group.id}

    @api.model
    def app_add_member_to_group(self, group_id, member_id, requester_partner_id=None, requester_staff_id=None):
        mode, scope = self.env['res.partner']._church_caller_scope(requester_partner_id, requester_staff_id)
        if mode == 'denied':
            return {'success': False, 'error': 'Not authorized'}

        group = self.sudo().browse(group_id)
        if not group.exists():
            return {'success': False, 'error': 'Group not found'}

        allowed = mode in ('all', 'assigned') or (mode == 'self' and group.leader_id.id == scope)
        if not allowed:
            return {'success': False, 'error': 'Only the group leader, a pastor or an admin can add members'}

        group.sudo().write({'member_ids': [(4, member_id)]})
        return {'success': True}
