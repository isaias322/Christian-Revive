# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request

from .base import (API, api_endpoint, get_json_body, json_response,
                   serialize_listing, serialize_order, serialize_review,
                   serialize_shop, dt)


class MarketplaceApiShops(http.Controller):

    # ------------------------------------------------------------------
    # Public shop pages
    # ------------------------------------------------------------------
    @http.route(API + '/shops/<int:shop_id>', type='http', auth='public',
                methods=['GET'], csrf=False)
    @api_endpoint(auth_required=False)
    def shop_detail(self, shop_id, api_user=None, **kw):
        seller = request.env['marketplace.seller'].sudo().browse(shop_id)
        if not seller.exists() or seller.state not in ('approved', 'suspended'):
            raise request.not_found()
        partner = api_user.partner_id if api_user else None
        Product = request.env['product.template'].sudo()
        listings = Product.search(
            Product.marketplace_search_domain({'seller_id': seller.id}),
            order='create_date desc', limit=60)
        reviews = request.env['marketplace.review'].sudo().search([
            ('seller_id', '=', seller.id), ('state', '=', 'published')],
            limit=20)
        data = serialize_shop(seller, partner, detail=True)
        data['listings'] = [serialize_listing(r, partner) for r in listings]
        data['reviews'] = [serialize_review(r) for r in reviews]
        return json_response(data)

    @http.route(API + '/shops/<int:shop_id>/follow', type='http',
                auth='public', methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def shop_follow(self, shop_id, api_user=None, **kw):
        seller = request.env['marketplace.seller'].sudo().browse(shop_id)
        if not seller.exists():
            raise request.not_found()
        state = seller.action_toggle_follow(api_user.partner_id)
        return json_response({
            'is_following': state,
            'follower_count': seller.follower_count,
        })

    # ------------------------------------------------------------------
    # My shop (seller side)
    # ------------------------------------------------------------------
    @http.route(API + '/shops', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def shop_create(self, api_user=None, **kw):
        partner = api_user.partner_id
        if partner.sudo().get_marketplace_seller():
            return json_response(error='You already have a shop.',
                                 status=409, error_code='duplicate')
        body = get_json_body()
        name = (body.get('name') or '').strip()
        if not name:
            return json_response(error='Shop name is required.',
                                 status=400, error_code='validation')
        Seller = request.env['marketplace.seller'].sudo()
        seller = Seller.create({
            'name': name,
            'slug': Seller._slugify(name),
            'partner_id': partner.id,
            'bio': body.get('bio') or False,
            'city': body.get('city') or False,
            'instagram_handle': body.get('instagram_handle') or False,
            'whatsapp_number': body.get('whatsapp_number') or False,
            'state': 'approved',
        })
        if body.get('logo'):
            self._set_image(seller, 'logo', body['logo'])
        return json_response(
            serialize_shop(seller, partner, detail=True), status=201)

    @http.route(API + '/shops/me', type='http', auth='public',
                methods=['GET'], csrf=False)
    @api_endpoint(auth_required=True)
    def my_shop(self, api_user=None, **kw):
        seller = self._require_shop(api_user)
        if isinstance(seller, dict):
            return json_response(**seller)
        partner = api_user.partner_id
        data = serialize_shop(seller, partner, detail=True)
        data.update({
            'kyc_status': seller.kyc_status,
            'payout_method': seller.payout_method,
            'wallet_balance': seller.wallet_balance,
            'currency_symbol': seller.currency_id.symbol,
            'order_count': seller.order_count,
            'total_sales': seller.total_sales,
            'listing_counts': {
                'total': seller.listing_count,
                'active': seller.active_listing_count,
                'sold': seller.sold_listing_count,
            },
        })
        return json_response(data)

    @http.route(API + '/shops/me/analytics', type='http', auth='public',
                methods=['GET'], csrf=False)
    @api_endpoint(auth_required=True)
    def my_shop_analytics(self, api_user=None, **kw):
        seller = self._require_shop(api_user)
        if isinstance(seller, dict):
            return json_response(**seller)
        data = seller.get_sales_analytics()
        top = data.pop('top_listing')
        data['top_listing'] = ({
            'id': top.id, 'name': top.name,
            'image_url': '/api/v1/image/product.template/%s' % top.id,
        } if top else None)
        data['currency_symbol'] = seller.currency_id.symbol
        return json_response(data)

    @http.route(API + '/shops/me', type='http', auth='public',
                methods=['PUT', 'PATCH'], csrf=False)
    @api_endpoint(auth_required=True)
    def update_my_shop(self, api_user=None, **kw):
        seller = self._require_shop(api_user)
        if isinstance(seller, dict):
            return json_response(**seller)
        body = get_json_body()
        vals = {}
        for field in ('bio', 'city', 'instagram_handle', 'whatsapp_number',
                      'payout_method', 'bank_name', 'bank_account_title',
                      'bank_account_number', 'mobile_wallet_number'):
            if field in body:
                vals[field] = body[field] or False
        if body.get('name'):
            vals['name'] = body['name']
        if vals:
            seller.write(vals)
        if body.get('logo'):
            self._set_image(seller, 'logo', body['logo'])
        if body.get('banner'):
            self._set_image(seller, 'banner', body['banner'])
        return json_response(
            serialize_shop(seller, api_user.partner_id, detail=True))

    @http.route(API + '/shops/me/listings', type='http', auth='public',
                methods=['GET'], csrf=False)
    @api_endpoint(auth_required=True)
    def my_listings(self, api_user=None, state=None, **kw):
        seller = self._require_shop(api_user)
        if isinstance(seller, dict):
            return json_response(**seller)
        listings = seller.listing_ids
        if state:
            listings = listings.filtered(lambda l: l.listing_state == state)
        return json_response({
            'items': [serialize_listing(rec, api_user.partner_id)
                      for rec in listings.sorted('create_date', reverse=True)],
        })

    @http.route(API + '/shops/me/kyc', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def submit_kyc(self, api_user=None, **kw):
        seller = self._require_shop(api_user)
        if isinstance(seller, dict):
            return json_response(**seller)
        body = get_json_body()
        vals = {}
        if body.get('id_type'):
            vals['kyc_id_type'] = body['id_type']
        if body.get('id_number'):
            vals['kyc_id_number'] = body['id_number']
        if vals:
            seller.write(vals)
        attachments = []
        for index, doc in enumerate((body.get('documents') or [])[:4]):
            payload = doc.split(',', 1)[1] if doc.startswith('data:') else doc
            try:
                base64.b64decode(payload.encode('ascii'), validate=True)
            except Exception:
                continue
            attachment = request.env['ir.attachment'].sudo().create({
                'name': 'kyc-document-%s' % (index + 1),
                'datas': payload.encode('ascii'),
                'res_model': 'marketplace.seller',
                'res_id': seller.id,
            })
            attachments.append(attachment.id)
        if attachments:
            seller.write({'kyc_document_ids': [(4, a) for a in attachments]})
        seller.action_submit_kyc()
        return json_response({'kyc_status': seller.kyc_status})

    # ------------------------------------------------------------------
    # Wallet & payouts
    # ------------------------------------------------------------------
    @http.route(API + '/shops/me/wallet', type='http', auth='public',
                methods=['GET'], csrf=False)
    @api_endpoint(auth_required=True)
    def my_wallet(self, api_user=None, **kw):
        seller = self._require_shop(api_user)
        if isinstance(seller, dict):
            return json_response(**seller)
        return json_response({
            'balance': seller.wallet_balance,
            'currency_symbol': seller.currency_id.symbol,
            'kyc_status': seller.kyc_status,
            'transactions': [{
                'id': tx.id,
                'type': tx.transaction_type,
                'amount': tx.signed_amount,
                'note': tx.note or None,
                'created_at': dt(tx.create_date),
            } for tx in seller.wallet_transaction_ids],
            'payouts': [{
                'id': p.id,
                'name': p.name,
                'amount': p.amount,
                'state': p.state,
                'paid_at': dt(p.paid_date),
            } for p in seller.payout_ids],
        })

    @http.route(API + '/shops/me/payouts', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def request_payout(self, api_user=None, **kw):
        seller = self._require_shop(api_user)
        if isinstance(seller, dict):
            return json_response(**seller)
        body = get_json_body()
        payout = request.env['marketplace.seller.payout'].request_payout(
            seller, body.get('amount') or 0)
        return json_response({
            'id': payout.id,
            'name': payout.name,
            'amount': payout.amount,
            'state': payout.state,
        }, status=201)

    # ------------------------------------------------------------------
    # Seller orders
    # ------------------------------------------------------------------
    @http.route(API + '/shops/me/orders', type='http', auth='public',
                methods=['GET'], csrf=False)
    @api_endpoint(auth_required=True)
    def my_shop_orders(self, api_user=None, **kw):
        seller = self._require_shop(api_user)
        if isinstance(seller, dict):
            return json_response(**seller)
        orders = request.env['sale.order'].sudo().search([
            ('marketplace_seller_id', '=', seller.id),
            ('state', '=', 'sale')], order='create_date desc')
        return json_response({
            'items': [serialize_order(o, role='seller') for o in orders],
        })

    @http.route(API + '/shops/me/orders/<int:order_id>/ship', type='http',
                auth='public', methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def ship_order(self, order_id, api_user=None, **kw):
        seller = self._require_shop(api_user)
        if isinstance(seller, dict):
            return json_response(**seller)
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.marketplace_seller_id != seller:
            raise request.not_found()
        body = get_json_body()
        order.action_mark_shipped(
            tracking_number=body.get('tracking_number'),
            courier_id=body.get('courier_id'))
        template = request.env.ref(
            'marketplace_core.mail_template_order_shipped',
            raise_if_not_found=False)
        if template:
            template.sudo().send_mail(order.id)
        return json_response(serialize_order(order, role='seller'))

    @http.route(API + '/shops/me/orders/<int:order_id>/label', type='http',
                auth='public', methods=['GET'], csrf=False)
    def order_label(self, order_id, token=None, **kw):
        """Serves the label PDF. Accepts the token as a query param, not
        just the Authorization header — this link is meant to be opened
        directly in an external browser/PDF viewer (e.g. via
        url_launcher on mobile), which won't attach custom headers."""
        header = request.httprequest.headers.get('Authorization', '')
        header_token = (header[7:].strip()
                        if header.lower().startswith('bearer ') else '')
        user = request.env['marketplace.api.token'].sudo().resolve(
            token or header_token)
        if not user:
            return json_response(error='Authentication required.',
                                 status=401, error_code='unauthorized')
        seller = user.partner_id.sudo().get_marketplace_seller()
        order = request.env['sale.order'].sudo().browse(order_id)
        if not seller or not order.exists() or \
                order.marketplace_seller_id != seller:
            raise request.not_found()
        attachment = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'sale.order'), ('res_id', '=', order.id),
            ('name', '=', 'shipping-label-%s.pdf' % order.name)], limit=1)
        if not attachment:
            return request.not_found()
        return request.make_response(
            base64.b64decode(attachment.datas),
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition',
                 'inline; filename="%s"' % attachment.name),
            ])

    # ------------------------------------------------------------------
    def _require_shop(self, api_user):
        seller = api_user.partner_id.sudo().get_marketplace_seller()
        if not seller:
            return {'error': 'You do not have a shop yet.',
                    'status': 404, 'error_code': 'no_shop'}
        return seller

    def _set_image(self, record, field, payload):
        if payload.startswith('data:'):
            payload = payload.split(',', 1)[1]
        try:
            base64.b64decode(payload.encode('ascii'), validate=True)
            record.write({field: payload.encode('ascii')})
        except Exception:
            pass
