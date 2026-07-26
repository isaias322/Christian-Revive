# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from .base import (API, api_endpoint, get_json_body, json_response,
                   serialize_order, serialize_review)


class MarketplaceApiOrders(http.Controller):

    def _buyer_order(self, order_id, api_user):
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or not order.is_marketplace_order or \
                order.partner_id != api_user.partner_id:
            raise request.not_found()
        return order

    @http.route(API + '/orders', type='http', auth='public', methods=['GET'],
                csrf=False)
    @api_endpoint(auth_required=True)
    def orders(self, api_user=None, **kw):
        records = request.env['sale.order'].sudo().search([
            ('is_marketplace_order', '=', True),
            ('partner_id', '=', api_user.partner_id.id),
            ('state', '!=', 'cancel'),
        ], order='create_date desc')
        return json_response({
            'items': [serialize_order(o) for o in records],
        })

    @http.route(API + '/orders/<int:order_id>', type='http', auth='public',
                methods=['GET'], csrf=False)
    @api_endpoint(auth_required=True)
    def order_detail(self, order_id, api_user=None, **kw):
        order = self._buyer_order(order_id, api_user)
        data = serialize_order(order)
        has_review = bool(request.env['marketplace.review'].sudo().search_count([
            ('order_id', '=', order.id),
            ('reviewer_id', '=', api_user.partner_id.id)]))
        data['has_review'] = has_review
        data['disputes'] = [{
            'id': d.id,
            'name': d.name,
            'reason': d.reason,
            'state': d.state,
        } for d in order.dispute_ids]
        return json_response(data)

    @http.route(API + '/orders/<int:order_id>/confirm-delivery', type='http',
                auth='public', methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def confirm_delivery(self, order_id, api_user=None, **kw):
        order = self._buyer_order(order_id, api_user)
        order.action_confirm_delivery()
        template = request.env.ref(
            'marketplace_core.mail_template_escrow_released',
            raise_if_not_found=False)
        if template:
            template.sudo().send_mail(order.id)
        return json_response(serialize_order(order))

    @http.route(API + '/orders/<int:order_id>/mto/balance-session',
                type='http', auth='public', methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def mto_balance_session(self, order_id, api_user=None, **kw):
        order = self._buyer_order(order_id, api_user)
        if not order.is_mto_order:
            return json_response(error='Not a made-to-order order.',
                                 status=400, error_code='validation')
        root = request.httprequest.url_root.rstrip('/')
        url = request.env['marketplace.cart.item'].create_mto_balance_stripe_session(
            order, success_url=root + '/market/order/thanks',
            cancel_url=root + '/market/orders/%s' % order.id)
        return json_response({'checkout_url': url})

    @http.route(API + '/orders/<int:order_id>/mto/pay-balance-manual',
                type='http', auth='public', methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def mto_pay_balance_manual(self, order_id, api_user=None, **kw):
        """For offline payment methods (COD/JazzCash/EasyPaisa/bank): the
        buyer confirms they've arranged payment directly with the seller,
        same trust-then-reconcile pattern the rest of checkout uses for
        these methods."""
        order = self._buyer_order(order_id, api_user)
        if not order.is_mto_order:
            return json_response(error='Not a made-to-order order.',
                                 status=400, error_code='validation')
        order.action_mto_confirm_balance_paid()
        return json_response(serialize_order(order))

    @http.route(API + '/orders/<int:order_id>/disputes', type='http',
                auth='public', methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def open_dispute(self, order_id, api_user=None, **kw):
        order = self._buyer_order(order_id, api_user)
        body = get_json_body()
        dispute = request.env['marketplace.dispute'].open_for_order(
            order, api_user.partner_id,
            body.get('reason') or 'other',
            body.get('description'))
        return json_response({
            'id': dispute.id,
            'name': dispute.name,
            'state': dispute.state,
        }, status=201)

    @http.route(API + '/orders/<int:order_id>/reviews', type='http',
                auth='public', methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def create_review(self, order_id, api_user=None, **kw):
        order = self._buyer_order(order_id, api_user)
        body = get_json_body()
        try:
            rating = int(body.get('rating') or 0)
        except (TypeError, ValueError):
            rating = 0
        if rating not in (1, 2, 3, 4, 5):
            return json_response(error='Rating must be 1-5.', status=400,
                                 error_code='validation')
        review = request.env['marketplace.review'].create_for_order(
            order, api_user.partner_id, rating, body.get('comment'))
        return json_response(serialize_review(review), status=201)
