# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ChurchGiveCategory(models.Model):
    _name        = 'church.give.category'
    _description = 'Donation Category'
    _order       = 'sequence, name'

    name     = fields.Char(string='Category Name', required=True, translate=True)
    code     = fields.Char(string='Code', required=True)
    icon     = fields.Char(string='Emoji Icon', default='💝')
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    is_active = fields.Boolean(string='Active', default=True)
    color    = fields.Integer(string='Color Index')

    transaction_count = fields.Integer(
        string='Transactions', compute='_compute_stats')
    total_raised = fields.Float(
        string='Total Raised (PKR)', compute='_compute_stats', digits=(16, 0))

    @api.depends()
    def _compute_stats(self):
        for cat in self:
            txs = self.env['church.give.transaction'].search([
                ('category_id', '=', cat.id),
                ('state', '=', 'completed'),
            ])
            cat.transaction_count = len(txs)
            cat.total_raised = sum(txs.mapped('amount_pkr'))