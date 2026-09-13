from odoo import models, fields, api


class ChurchGiveFund(models.Model):
    _name = 'church.give.fund'
    _description = 'Restricted / Designated Fund'
    _order = 'name'

    name = fields.Char(string='Fund Name', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    fund_type = fields.Selection([
        ('general', 'General'),
        ('restricted', 'Restricted'),
        ('designated', 'Designated'),
    ], string='Fund Type', default='general', required=True)
    is_active = fields.Boolean(string='Active', default=True)

    total_contributed = fields.Float(
        string='Total Contributed (PKR equiv.)',
        compute='_compute_total_contributed', digits=(16, 2))
    pledge_ids = fields.One2many('church.give.pledge', 'fund_id', string='Pledges')

    def _compute_total_contributed(self):
        Transaction = self.env['church.give.transaction']
        for fund in self:
            txs = Transaction.sudo().search([
                ('fund_id', '=', fund.id), ('state', '=', 'completed'),
            ])
            fund.total_contributed = sum(txs.mapped('amount_pkr'))

    @api.model
    def app_get_funds(self):
        funds = self.sudo().search([('is_active', '=', True)], order='name')
        return {'success': True, 'funds': [{
            'id': f.id, 'name': f.name, 'code': f.code or '',
            'fund_type': f.fund_type, 'description': f.description or '',
            'total_contributed': f.total_contributed,
        } for f in funds]}
