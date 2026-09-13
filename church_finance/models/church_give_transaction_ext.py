from odoo import models, fields, api


class ChurchGiveTransactionExt(models.Model):
    _inherit = 'church.give.transaction'

    pledge_id = fields.Many2one('church.give.pledge', string='Applied to Pledge')
    fund_id = fields.Many2one('church.give.fund', string='Fund')

    @api.model
    def app_record_transaction(self, *args, **kwargs):
        # Mirror church_give's own arg-unwrapping so we read pledge_id the
        # same way the parent method reads everything else, regardless of
        # whether the caller sent it positionally or as a kwarg.
        clean_args = [a for a in args if a != []]
        data = kwargs if kwargs else (clean_args[0] if clean_args else {})
        pledge_id = data.get('pledge_id')

        result = super().app_record_transaction(*args, **kwargs)

        if isinstance(result, dict) and result.get('success') and pledge_id:
            odoo_id = result.get('odoo_id')
            if odoo_id:
                self.sudo().browse(int(odoo_id)).write({'pledge_id': int(pledge_id)})

        return result
