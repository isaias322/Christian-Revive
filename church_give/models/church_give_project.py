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
        data = self.env['church.give.transaction'].read_group(
            [('project_id', 'in', self.ids), ('state', '=', 'completed')],
            ['project_id', 'amount_pkr'],
            ['project_id'],
        )
        totals = {row['project_id'][0]: row['amount_pkr'] for row in data if row['project_id']}
        for proj in self:
            proj.raised_amount = totals.get(proj.id, 0.0)

    @api.depends()
    def _compute_transaction_count(self):
        data = self.env['church.give.transaction'].read_group(
            [('project_id', 'in', self.ids), ('state', '=', 'completed')],
            ['project_id'],
            ['project_id'],
        )
        counts = {row['project_id'][0]: row['project_id_count'] for row in data if row['project_id']}
        for proj in self:
            proj.transaction_count = counts.get(proj.id, 0)

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