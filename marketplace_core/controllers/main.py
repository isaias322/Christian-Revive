# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging
import time

from odoo import http
from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)


class MarketplaceWebsiteSale(WebsiteSale):
    """Marketplace listings live on /market, not the default /shop —
    bounce anyone who lands on the eCommerce product page directly
    (bookmark, search engine, shared link, ...) to the marketplace item
    page instead of showing Odoo's generic shop template for it."""

    @route()
    def product(self, product, category=None, pricelist=None, **kwargs):
        if product and product.is_marketplace_listing:
            return request.redirect('/market/item/%s' % product.id, code=301)
        return super().product(
            product, category=category, pricelist=pricelist, **kwargs)


class MarketplaceStripeWebhook(http.Controller):
    """Fulfils marketplace orders once Stripe confirms a card payment.

    Shared by the website and the mobile app — both just create a Stripe
    Checkout Session and send the buyer to Stripe's hosted page; this is
    the one place that actually books the order, once payment is real.
    """

    @http.route('/payment/stripe/webhook', type='http', auth='public',
                methods=['POST'], csrf=False, save_session=False)
    def stripe_webhook(self, **kw):
        payload = request.httprequest.get_data()
        secret = request.env['ir.config_parameter'].sudo().get_param(
            'marketplace_core.stripe_webhook_secret')
        if not secret:
            _logger.warning('Stripe webhook called but no signing secret '
                            'configured — rejecting.')
            return request.make_json_response(
                {'error': 'webhook not configured'}, status=503)
        sig_header = request.httprequest.headers.get('Stripe-Signature', '')
        if not self._verify_signature(payload, sig_header, secret):
            _logger.warning('Stripe webhook signature verification failed.')
            return request.make_json_response(
                {'error': 'invalid signature'}, status=400)

        event = json.loads(payload)
        if event.get('type') == 'checkout.session.completed':
            self._fulfill_session(event['data']['object'])
        return request.make_json_response({'received': True})

    def _verify_signature(self, payload, sig_header, secret):
        try:
            parts = dict(
                p.split('=', 1) for p in sig_header.split(',') if '=' in p)
            timestamp, signature = parts['t'], parts['v1']
        except (KeyError, ValueError):
            return False
        if abs(time.time() - int(timestamp)) > 300:
            return False
        signed_payload = ('%s.' % timestamp).encode() + payload
        expected = hmac.new(
            secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _fulfill_session(self, session):
        metadata = session.get('metadata') or {}
        partner_id = metadata.get('partner_id')
        item_ids_raw = metadata.get('cart_item_ids')
        if not partner_id or not item_ids_raw:
            _logger.error('Stripe session %s missing marketplace metadata',
                          session.get('id'))
            return
        partner = request.env['res.partner'].sudo().browse(int(partner_id))
        item_ids = [int(i) for i in item_ids_raw.split(',') if i]
        values = {
            'name': metadata.get('name'),
            'phone': metadata.get('phone'),
            'street': metadata.get('street'),
            'city': metadata.get('city'),
            'zip': metadata.get('zip') or False,
            'courier_id': metadata.get('courier_id') or False,
            'payment_method': 'card',
        }
        try:
            orders = request.env['marketplace.cart.item'].sudo().checkout(
                partner, values, item_ids=item_ids)
            orders.write({'payment_received': True})
            _logger.info('Stripe session %s fulfilled: orders %s',
                        session.get('id'), orders.mapped('name'))
        except Exception:
            # Retried deliveries for an already-fulfilled session land here
            # too (the cart items are gone by then) — logged, not re-raised,
            # since Stripe retries on any non-2xx response.
            _logger.exception('Failed to fulfil Stripe session %s',
                              session.get('id'))
