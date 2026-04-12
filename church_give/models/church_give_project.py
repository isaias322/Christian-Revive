# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ChurchGiveProject(models.Model):
    _name        = 'church.give.project'
    _description = 'Church Giving Project'
    _order       = 'sequence, name'

    name        = fields.Char(string='Project Name', required=True)
    code        = fields.Char(string='Code', required=True)
    icon        = fields.Char(string='Emoji Icon', default='📺')
    description = fields.Text(string='Description')
    goal_amount = fields.Float(string='Goal Amount (PKR)', digits=(16, 0))
    sequence    = fields.Integer(default=10)
    is_active   = fields.Boolean(string='Active', default=True)
    color       = fields.Integer(string='Color')

    raised_amount = fields.Float(
        string='Raised Amount (PKR)',
        compute='_compute_raised_amount',
        store=True, digits=(16, 0))

    transaction_count = fields.Integer(
        string='Donations',
        compute='_compute_transaction_count')

    progress_percent = fields.Float(
        string='Progress %',
        compute='_compute_progress')

    @api.depends()
    def _compute_raised_amount(self):
        for proj in self:
            txs = self.env['church.give.transaction'].search([
                ('project_id', '=', proj.id),
                ('state', '=', 'completed'),
            ])
            proj.raised_amount = sum(txs.mapped('amount_pkr'))

    @api.depends()
    def _compute_transaction_count(self):
        for proj in self:
            proj.transaction_count = self.env['church.give.transaction'].search_count([
                ('project_id', '=', proj.id),
                ('state', '=', 'completed'),
            ])

    @api.depends('raised_amount', 'goal_amount')
    def _compute_progress(self):
        for proj in self:
            if proj.goal_amount > 0:
                proj.progress_percent = min(
                    100.0, (proj.raised_amount / proj.goal_amount) * 100)
            else:
                proj.progress_percent = 0.0

    @api.constrains('code')
    def _check_unique_code(self):
        for rec in self:
            if self.search_count([
                ('code', '=', rec.code),
                ('id', '!=', rec.id)
            ]) > 0:
                raise ValidationError('Project code must be unique.')