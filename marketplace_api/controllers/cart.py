# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from .base import (API, api_endpoint, get_json_body, json_response,
                   serialize_order)


class MarketplaceApiCart(http.Controller):

    def _cart_payload(self, partner):
        items = request.env['marketplace.cart.item'].get_cart(partner)
        icp = request.env['ir.config_parameter'].sudo()
        fixed = float(icp.get_param(
            'marketplace_core.buyer_protection_fixed', '100.0'))
        pct = float(icp.get_param(
            'marketplace_core.buyer_protection_pct', '5.0'))
        subtotal = sum(items.mapped('price'))
        protection = (fixed + subtotal * pct / 100.0) if items else 0.0
        return {
            'items': [{
                'id': item.id,
                'listing_id': item.product_tmpl_id.id,
                'name': item.product_tmpl_id.name,
                'price': item.price,
                'image_url': '/api/v1/image/product.template/%s'
                             % item.product_tmpl_id.id,
                'seller_id': item.seller_id.id,
                'seller_name': item.seller_id.name,
            } for item in items],
            'subtotal': subtotal,
            'buyer_protection_fee': protection,
            'total': subtotal + protection,
            'currency_symbol': request.env.company.currency_id.symbol,
        }

    @http.route(API + '/cart', type='http', auth='public', methods=['GET'],
                csrf=False)
    @api_endpoint(auth_required=True)
    def cart(self, api_user=None, **kw):
        return json_response(self._cart_payload(api_user.partner_id))

    @http.route(API + '/cart/add', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def cart_add(self, api_user=None, **kw):
        body = get_json_body()
        listing = request.env['product.template'].sudo().browse(
            int(body.get('listing_id') or 0))
        if not listing.exists() or not listing.is_marketplace_listing:
            raise request.not_found()
        request.env['marketplace.cart.item'].add_item(
            api_user.partner_id, listing)
        return json_response(self._cart_payload(api_user.partner_id))

    @http.route(API + '/cart/remove', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def cart_remove(self, api_user=None, **kw):
        body = get_json_body()
        item = request.env['marketplace.cart.item'].sudo().browse(
            int(body.get('item_id') or 0))
        if item.exists() and item.partner_id == api_user.partner_id:
            item.unlink()
        return json_response(self._cart_payload(api_user.partner_id))

    @http.route(API + '/checkout', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def checkout(self, api_user=None, **kw):
        body = get_json_body()
        values = {
            'name': body.get('name'),
            'phone': body.get('phone'),
            'street': body.get('street'),
            'city': body.get('city'),
            'zip': body.get('zip'),
            'payment_method': body.get('payment_method'),
            'courier_id': body.get('courier_id'),
        }
        if body.get('payment_method') == 'card':
            # No app-link/deep-link setup for this build, so card payment
            # opens Stripe's hosted page in an external browser; the buyer
            # returns to the app manually afterwards and refreshes their
            # orders (the actual order is booked by the webhook, not by
            # this request).
            root = request.httprequest.url_root.rstrip('/')
            url = request.env['marketplace.cart.item'].create_stripe_session(
                api_user.partner_id, values,
                success_url=root + '/market/order/thanks',
                cancel_url=root + '/market/cart')
            return json_response({'checkout_url': url}, status=200)
        orders = request.env['marketplace.cart.item'].checkout(
            api_user.partner_id, values)
        return json_response({
            'orders': [serialize_order(o) for o in orders],
        }, status=201)
