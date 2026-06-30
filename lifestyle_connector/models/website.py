# -*- coding: utf-8 -*-
from odoo import models
from odoo.http import request


class Website(models.Model):
    """Keeps the public shop restricted to the same products the Revive
    Lifestyle app shows. Odoo's own product_domain only filters by
    published-state for non-staff visitors, so an internal/admin preview
    (and any other product in this shared database) would otherwise leak
    through onto this storefront."""
    _inherit = 'website'

    def _product_domain(self):
        domain = super()._product_domain()
        domain = domain + self.env['product.template']._lifestyle_app_visibility_domain()

        # color_options/size_options are plain comma-separated Char fields,
        # not real Odoo attributes, so the native attribute filters can't
        # see them - the shop's color/size filter links read these instead.
        color = request.params.get('lifestyle_color')
        if color:
            domain = domain + [('color_options', 'ilike', color)]
        size = request.params.get('lifestyle_size')
        if size:
            domain = domain + [('size_options', 'ilike', size)]

        availability = request.params.get('lifestyle_availability')
        if availability == 'in_stock':
            domain = domain + ['|', ('type', 'not in', ('consu', 'product')), ('qty_available', '>', 0)]
        elif availability == 'out_of_stock':
            domain = domain + [('type', 'in', ('consu', 'product')), ('qty_available', '<=', 0)]

        year = request.params.get('lifestyle_year')
        if year:
            year = int(year)
            domain = domain + [
                ('create_date', '>=', f'{year}-01-01 00:00:00'),
                ('create_date', '<', f'{year + 1}-01-01 00:00:00'),
            ]
        return domain
