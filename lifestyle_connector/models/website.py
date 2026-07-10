# -*- coding: utf-8 -*-
from odoo import fields, models
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
        Product = self.env['product.template']
        # The Lifestyle /shop grid lists only the Lifestyle catalog - but
        # everything else that consults this domain (the product page's
        # add-to-cart possibility check, cart validation) must accept
        # products of EITHER storefront: the Christian Revive store sells
        # through the same product pages and cart. Restricting those to
        # Lifestyle-only made CR-only products show "no valid combination".
        path = request.httprequest.path if request else ''
        is_shop_listing = (
            path == '/shop'
            or path.startswith('/shop/page')
            or path.startswith('/shop/category')
        )
        if is_shop_listing:
            domain = domain + Product._lifestyle_app_visibility_domain()
        else:
            domain = (
                domain + ['|']
                + Product._lifestyle_app_visibility_domain()
                + Product._cr_app_visibility_domain()
            )

        # color_options/size_options are plain comma-separated Char fields,
        # not real Odoo attributes, so the native attribute filters can't
        # see them - the shop's color/size filter links read these instead.
        color = request.params.get('lifestyle_color')
        if color:
            domain = domain + [('color_options', 'ilike', color)]
        size = request.params.get('lifestyle_size')
        if size:
            domain = domain + [('size_options', 'ilike', size)]

        room = request.params.get('lifestyle_room')
        if room:
            domain = domain + [('lifestyle_room_ids', 'in', [int(room)])]

        quick = request.params.get('lifestyle_quick')
        if quick == 'new':
            domain = domain + [('create_date', '>=', fields.Datetime.subtract(fields.Datetime.now(), days=45))]
        elif quick == 'popular':
            sold_lines = self.env['sale.order.line'].sudo().search([
                ('order_id.state', 'in', ('sale', 'done')),
                ('product_id.product_tmpl_id', '!=', False),
            ])
            sold_template_ids = sold_lines.mapped('product_id.product_tmpl_id').ids
            domain = domain + [('id', 'in', sold_template_ids or [0])]
        availability = request.params.get('lifestyle_availability')
        if availability in ('in_stock', 'out_of_stock'):
            # qty_available in a public-user domain triggers an AccessError
            # (computing it reads stock.warehouse, which visitors can't).
            # Precompute the in-stock ids with sudo and filter by id.
            stockable = self.env['product.template'].sudo().search(
                [('is_storable', '=', True), ('sale_ok', '=', True)])
            in_stock_ids = stockable.filtered(lambda p: p.qty_available > 0).ids
            if availability == 'in_stock':
                domain = domain + ['|', ('is_storable', '=', False), ('id', 'in', in_stock_ids or [0])]
            else:
                domain = domain + [('is_storable', '=', True), ('id', 'not in', in_stock_ids or [0])]

        year = request.params.get('lifestyle_year')
        if year:
            year = int(year)
            domain = domain + [
                ('create_date', '>=', f'{year}-01-01 00:00:00'),
                ('create_date', '<', f'{year + 1}-01-01 00:00:00'),
            ]
        return domain
