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

    @api.model
    def app_get_transactions(self, *args, **kwargs):
        # church_give's own app_get_transactions has no idea pledge_id
        # exists (it's defined here, not there), so it never includes it —
        # the app's Giving History always showed the gift's Category and
        # silently dropped which pledge it was applied to. Stitch it back
        # in after the fact instead of duplicating the whole method.
        result = super().app_get_transactions(*args, **kwargs)
        if not isinstance(result, list):
            return result

        ids = [r.get('odoo_id') or r.get('id') for r in result if r.get('odoo_id') or r.get('id')]
        txs_by_id = {tx.id: tx for tx in self.sudo().browse(ids)}

        for r in result:
            tx = txs_by_id.get(r.get('odoo_id') or r.get('id'))
            pledge = tx.pledge_id if tx else False
            r['pledge_id'] = pledge.id if pledge else False
            # The app shows this as the payment's headline instead of the
            # giving Category whenever it's set — simply flags "this was a
            # pledge payment", distinct from a plain Tithe/Offering/Project
            # gift.
            r['pledge_label'] = 'Pledge' if pledge else ''

        return result
