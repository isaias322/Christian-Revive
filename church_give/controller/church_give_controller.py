# -*- coding: utf-8 -*-
"""
Webhook endpoints for payment gateway callbacks.

EasyPaisa, JazzCash, Stripe, PayPal all POST to these endpoints
when a payment status changes.

Register these routes in your Odoo nginx config:
    /give/webhook/easypaisa
    /give/webhook/jazzcash
    /give/webhook/stripe
    /give/webhook/paypal
"""
import json
import logging
import hashlib
import hmac

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class ChurchGiveController(http.Controller):

    # ── EasyPaisa callback ────────────────────────────────────
    @http.route('/give/webhook/easypaisa', type='http',
                auth='public', methods=['POST'], csrf=False)
    def easypaisa_webhook(self, **kwargs):
        try:
            data = request.get_json_data() or kwargs
            _logger.info('EasyPaisa webhook: %s', json.dumps(data))

            order_id   = data.get('orderId', '')
            response_code = data.get('responseCode', '')
            tx_id      = data.get('transactionId', '')

            tx = request.env['church.give.transaction'].sudo().search([
                ('app_transaction_id', '=', order_id)
            ], limit=1)

            if tx:
                if response_code == '00':
                    tx.write({
                        'state': 'completed',
                        'gateway_reference': tx_id,
                        'gateway_response': json.dumps(data),
                    })
                else:
                    tx.write({
                        'state': 'failed',
                        'gateway_response': json.dumps(data),
                    })

            return Response('OK', status=200)
        except Exception as e:
            _logger.error('EasyPaisa webhook error: %s', e)
            return Response('Error', status=500)

    # ── JazzCash callback ─────────────────────────────────────
    @http.route('/give/webhook/jazzcash', type='http',
                auth='public', methods=['POST'], csrf=False)
    def jazzcash_webhook(self, **kwargs):
        try:
            data = request.get_json_data() or kwargs
            _logger.info('JazzCash webhook: %s', json.dumps(data))

            ref_no        = data.get('pp_TxnRefNo', '')
            response_code = data.get('pp_ResponseCode', '')
            jc_ref        = data.get('pp_TxnRefNo', '')

            tx = request.env['church.give.transaction'].sudo().search([
                ('app_transaction_id', '=', ref_no)
            ], limit=1)

            if tx:
                if response_code == '000':
                    tx.write({
                        'state': 'completed',
                        'gateway_reference': jc_ref,
                        'gateway_response': json.dumps(data),
                    })
                else:
                    tx.write({
                        'state': 'failed',
                        'gateway_response': json.dumps(data),
                    })

            return Response('OK', status=200)
        except Exception as e:
            _logger.error('JazzCash webhook error: %s', e)
            return Response('Error', status=500)

    # ── Stripe webhook ────────────────────────────────────────
    @http.route('/give/webhook/stripe', type='http',
                auth='public', methods=['POST'], csrf=False)
    def stripe_webhook(self, **kwargs):
        """
        Stripe sends signed webhook events.
        Set STRIPE_WEBHOOK_SECRET in your Odoo system parameters.
        """
        try:
            payload   = request.httprequest.get_data(as_text=True)
            sig_header = request.httprequest.headers.get('Stripe-Signature', '')

            # Verify Stripe signature
            webhook_secret = request.env['ir.config_parameter'].sudo().get_param(
                'church_give.stripe_webhook_secret', '')

            if webhook_secret:
                if not _verify_stripe_signature(payload, sig_header, webhook_secret):
                    _logger.warning('Stripe webhook: invalid signature')
                    return Response('Invalid signature', status=400)

            event = json.loads(payload)
            _logger.info('Stripe webhook event: %s', event.get('type'))

            if event['type'] == 'payment_intent.succeeded':
                pi = event['data']['object']
                order_id = pi.get('metadata', {}).get('order_id', '')
                tx = request.env['church.give.transaction'].sudo().search([
                    ('app_transaction_id', '=', order_id)
                ], limit=1)
                if tx:
                    tx.write({
                        'state': 'completed',
                        'gateway_reference': pi.get('id', ''),
                        'gateway_response': json.dumps(pi),
                    })

            elif event['type'] == 'payment_intent.payment_failed':
                pi = event['data']['object']
                order_id = pi.get('metadata', {}).get('order_id', '')
                tx = request.env['church.give.transaction'].sudo().search([
                    ('app_transaction_id', '=', order_id)
                ], limit=1)
                if tx:
                    tx.write({
                        'state': 'failed',
                        'gateway_response': json.dumps(pi),
                    })

            return Response(json.dumps({'received': True}),
                            content_type='application/json', status=200)
        except Exception as e:
            _logger.error('Stripe webhook error: %s', e)
            return Response('Error', status=500)

    # ── PayPal webhook ────────────────────────────────────────
    @http.route('/give/webhook/paypal', type='http',
                auth='public', methods=['POST'], csrf=False)
    def paypal_webhook(self, **kwargs):
        try:
            data = request.get_json_data() or {}
            _logger.info('PayPal webhook event: %s', data.get('event_type'))

            event_type = data.get('event_type', '')
            resource   = data.get('resource', {})

            if event_type == 'PAYMENT.CAPTURE.COMPLETED':
                ref = (resource.get('supplementary_data', {})
                       .get('related_ids', {})
                       .get('order_id', ''))
                tx = request.env['church.give.transaction'].sudo().search([
                    ('gateway_reference', '=', ref)
                ], limit=1)
                if tx:
                    tx.write({
                        'state': 'completed',
                        'gateway_response': json.dumps(resource),
                    })

            elif event_type == 'PAYMENT.CAPTURE.DENIED':
                ref = resource.get('id', '')
                tx = request.env['church.give.transaction'].sudo().search([
                    ('gateway_reference', '=', ref)
                ], limit=1)
                if tx:
                    tx.write({
                        'state': 'failed',
                        'gateway_response': json.dumps(resource),
                    })

            return Response('OK', status=200)
        except Exception as e:
            _logger.error('PayPal webhook error: %s', e)
            return Response('Error', status=500)

    # ── Health check ──────────────────────────────────────────
    @http.route('/give/ping', type='http', auth='public', methods=['GET'])
    def ping(self, **kwargs):
        return Response(
            json.dumps({'status': 'ok', 'module': 'church_give'}),
            content_type='application/json',
            status=200,
        )


def _verify_stripe_signature(payload: str, sig_header: str, secret: str) -> bool:
    """Verify Stripe webhook signature."""
    try:
        parts = {k: v for part in sig_header.split(',')
                 for k, v in [part.split('=', 1)]}
        timestamp = parts.get('t', '')
        sig       = parts.get('v1', '')
        signed    = f'{timestamp}.{payload}'
        expected  = hmac.new(
            secret.encode(), signed.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, sig)
    except Exception:
        return False