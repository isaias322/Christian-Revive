from odoo import models, fields


class ChurchGiveTransactionExt(models.Model):
    _inherit = 'church.give.transaction'

    pledge_id = fields.Many2one('church.give.pledge', string='Applied to Pledge')
    fund_id = fields.Many2one('church.give.fund', string='Fund')
