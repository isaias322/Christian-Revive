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
