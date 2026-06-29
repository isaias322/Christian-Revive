# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from .api import _current_partner


class LifestyleWebsiteReviews(http.Controller):

    @http.route('/shop/product/<int:product_id>/review/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def submit_product_review(self, product_id, rating=None, comment=None, **kwargs):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.redirect('/shop')

        partner = _current_partner()
        if not partner:
            return request.redirect(f'/web/login?redirect={product.website_url}')

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            rating = 0
        if 1 <= rating <= 5:
            Review = request.env['lifestyle.product.review'].sudo()
            existing = Review.search([
                ('product_tmpl_id', '=', product.id),
                ('partner_id', '=', partner.id),
            ], limit=1)
            vals = {'rating': rating, 'comment': (comment or '').strip()}
            if existing:
                existing.write(vals)
            else:
                Review.create({**vals, 'product_tmpl_id': product.id, 'partner_id': partner.id})

        return request.redirect(f'{product.website_url}#reviews')
