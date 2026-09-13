from odoo import models, fields, api


class ChurchFamily(models.Model):
    _name = 'church.family'
    _description = 'Church Family / Household'
    _order = 'name'

    name = fields.Char(string='Family Name', required=True)
    head_id = fields.Many2one(
        'res.partner', string='Family Head',
        domain=[('is_member', '=', True)],
    )
    member_ids = fields.One2many('res.partner', 'family_id', string='Family Members')
    member_count = fields.Integer(string='Members', compute='_compute_member_count')

    @api.depends('member_ids')
    def _compute_member_count(self):
        for family in self:
            family.member_count = len(family.member_ids)

    # ── Church Management RPC ────────────────────────────────────

    @api.model
    def app_get_families(self, requester_staff_id=None):
        mode, _scope = self.env['res.partner']._church_caller_scope(
            requester_staff_id=requester_staff_id)
        if mode not in ('all', 'assigned'):
            return {'success': False, 'error': 'Not authorized'}
        families = self.sudo().search([], order='name')
        return {'success': True, 'families': [{
            'id': f.id, 'name': f.name,
            'head_id': f.head_id.id if f.head_id else False,
            'head_name': f.head_id.name if f.head_id else '',
            'member_count': f.member_count,
        } for f in families]}

    @api.model
    def app_get_family_detail(self, family_id, requester_staff_id=None):
        mode, _scope = self.env['res.partner']._church_caller_scope(
            requester_staff_id=requester_staff_id)
        if mode not in ('all', 'assigned'):
            return {'success': False, 'error': 'Not authorized'}
        family = self.sudo().browse(family_id)
        if not family.exists():
            return {'success': False, 'error': 'Family not found'}
        return {
            'success': True,
            'family': {
                'id': family.id, 'name': family.name,
                'head_id': family.head_id.id if family.head_id else False,
            },
            'members': family.member_ids.read(
                ['id', 'name', 'membership_status', 'is_family_head']),
        }

    @api.model
    def app_create_family(self, vals, requester_staff_id=None):
        mode, _scope = self.env['res.partner']._church_caller_scope(
            requester_staff_id=requester_staff_id)
        if mode not in ('all', 'assigned'):
            return {'success': False, 'error': 'Not authorized to create families'}
        vals = dict(vals or {})
        if not vals.get('name'):
            return {'success': False, 'error': 'name is required'}
        family = self.sudo().create({'name': vals['name']})
        return {'success': True, 'family_id': family.id}

    @api.model
    def app_add_member_to_family(self, family_id, member_id, is_head=False,
                                  requester_staff_id=None):
        mode, _scope = self.env['res.partner']._church_caller_scope(
            requester_staff_id=requester_staff_id)
        if mode not in ('all', 'assigned'):
            return {'success': False, 'error': 'Not authorized'}
        family = self.sudo().browse(family_id)
        if not family.exists():
            return {'success': False, 'error': 'Family not found'}
        member = self.env['res.partner'].sudo().browse(member_id)
        if not member.exists():
            return {'success': False, 'error': 'Member not found'}

        if is_head:
            family.member_ids.write({'is_family_head': False})
            family.write({'head_id': member.id})
        # Force is_member True so this member actually shows up in the
        # family's roster — a blank checkbox here was the root cause of a
        # family silently not appearing in the app before.
        member.write({
            'family_id': family.id,
            'is_member': True,
            'is_family_head': is_head,
        })
        return {'success': True}

    @api.model
    def app_remove_member_from_family(self, member_id, requester_staff_id=None):
        mode, _scope = self.env['res.partner']._church_caller_scope(
            requester_staff_id=requester_staff_id)
        if mode not in ('all', 'assigned'):
            return {'success': False, 'error': 'Not authorized'}
        member = self.env['res.partner'].sudo().browse(member_id)
        if not member.exists():
            return {'success': False, 'error': 'Member not found'}
        was_head = member.is_family_head
        family = member.family_id
        member.write({'family_id': False, 'is_family_head': False})
        if was_head and family:
            family.write({'head_id': False})
        return {'success': True}
