# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from .api import _current_partner


class LifestyleWebsiteNotifications(http.Controller):

    @http.route('/shop/product/<int:product_id>/notify-stock', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def notify_stock(self, product_id, email=None, **kwargs):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return request.redirect('/shop')

        email = (email or '').strip()
        if email:
            partner = _current_partner()
            Notification = request.env['lifestyle.stock.notification'].sudo()
            existing = Notification.search([
                ('product_tmpl_id', '=', product.id),
                ('email', '=', email),
            ], limit=1)
            if not existing:
                Notification.create({
                    'product_tmpl_id': product.id,
                    'email': email,
                    'partner_id': partner.id if partner else False,
                })

        return request.redirect(f'{product.website_url}?notify_success=1#notify_stock')
