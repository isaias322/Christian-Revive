from odoo import models, fields, api


class ChurchBranch(models.Model):
    _name = 'church.branch'
    _description = 'Church Branch / Campus'
    _order = 'name'

    name = fields.Char(string='Branch Name', required=True)
    location = fields.Char(string='Location')
    timezone = fields.Char(string='Timezone', help='e.g. "Asia/Karachi"')
    is_active = fields.Boolean(string='Active', default=True)
    member_count = fields.Integer(string='Members', compute='_compute_member_count')

    def _compute_member_count(self):
        for branch in self:
            branch.member_count = self.env['res.partner'].sudo().search_count([
                ('branch_id', '=', branch.id),
            ])

    @api.model
    def app_get_branches(self):
        branches = self.sudo().search([('is_active', '=', True)], order='name')
        return {'success': True, 'branches': [{
            'id': b.id, 'name': b.name, 'location': b.location or '',
        } for b in branches]}


class ResPartnerBranch(models.Model):
    _inherit = 'res.partner'

    branch_id = fields.Many2one('church.branch', string='Branch / Campus')


class CellGroupBranch(models.Model):
    _inherit = 'cell.group'

    branch_id = fields.Many2one('church.branch', string='Branch / Campus')
