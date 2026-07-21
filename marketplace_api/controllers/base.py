# -*- coding: utf-8 -*-
"""Shared plumbing for the mobile REST API.

All endpoints are plain `type='http'` routes returning JSON so the mobile
app talks straightforward REST (no JSON-RPC envelope). Authentication is a
Bearer token resolved through `marketplace.api.token`.
"""
import functools
import json
import logging

from werkzeug.exceptions import HTTPException

from odoo import fields, http
from odoo.exceptions import AccessDenied, UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

API = '/api/v1'


def json_response(data=None, status=200, error=None, error_code=None):
    payload = {'success': error is None}
    if error is not None:
        payload['error'] = error
        if error_code:
            payload['error_code'] = error_code
    if data is not None:
        payload['data'] = data
    return request.make_json_response(payload, status=status)


def get_json_body():
    try:
        raw = request.httprequest.get_data(as_text=True)
        return json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        return {}


def get_auth_user():
    """Resolve the Bearer token to a res.users record (empty if invalid)."""
    header = request.httprequest.headers.get('Authorization', '')
    token = header[7:].strip() if header.lower().startswith('bearer ') else ''
    return request.env['marketplace.api.token'].sudo().resolve(token)


def api_endpoint(auth_required=True):
    """Decorator: JSON error handling + optional token authentication.

    Passes the authenticated user as the `api_user` kwarg.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            user = get_auth_user()
            if auth_required and not user:
                return json_response(
                    error='Authentication required.', status=401,
                    error_code='unauthorized')
            try:
                return func(self, *args, api_user=user, **kwargs)
            except (UserError, ValidationError) as e:
                # Discard partial writes: we swallow the exception, so the
                # framework will not roll back for us.
                request.env.cr.rollback()
                return json_response(error=str(e), status=400,
                                     error_code='validation')
            except AccessDenied:
                request.env.cr.rollback()
                return json_response(error='Access denied.', status=403,
                                     error_code='forbidden')
            except HTTPException as e:
                request.env.cr.rollback()
                return json_response(
                    error=e.description or 'Not found.',
                    status=e.code or 404, error_code='not_found')
            except Exception:
                _logger.exception('Unhandled API error in %s', func.__name__)
                request.env.cr.rollback()
                return json_response(
                    error='Internal server error.', status=500,
                    error_code='server_error')
        return wrapper
    return decorator


# ----------------------------------------------------------------------
# Serializers
# ----------------------------------------------------------------------
def dt(value):
    return fields.Datetime.to_string(value) if value else None


def serialize_listing(listing, partner=None, detail=False):
    data = {
        'id': listing.id,
        'name': listing.name,
        'price': listing.list_price,
        'original_price': listing.original_price or None,
        'currency': listing.currency_id.name,
        'currency_symbol': listing.currency_id.symbol,
        'condition': listing.condition,
        'state': listing.listing_state,
        'stock_quantity': listing.stock_quantity,
        'brand': listing.marketplace_brand_id.name or None,
        'brand_id': listing.marketplace_brand_id.id or None,
        'size': listing.marketplace_size_id.name or None,
        'size_id': listing.marketplace_size_id.id or None,
        'category_id': listing.public_categ_ids[:1].id or None,
        'category': listing.public_categ_ids[:1].name or None,
        'image_url': '/api/v1/image/product.template/%s' % listing.id,
        'favorite_count': listing.favorite_count,
        'view_count': listing.view_count,
        'is_bumped': listing.is_bumped,
        'is_favorite': bool(partner) and listing.is_favorited_by(partner),
        'created_at': dt(listing.create_date),
        'seller': {
            'id': listing.marketplace_seller_id.id,
            'name': listing.marketplace_seller_id.name,
            'slug': listing.marketplace_seller_id.slug,
            'rating': round(listing.marketplace_seller_id.rating_avg, 1),
            'logo_url': '/api/v1/image/marketplace.seller/%s?field=logo'
                        % listing.marketplace_seller_id.id,
        } if listing.marketplace_seller_id else None,
    }
    if detail:
        data.update({
            'description': listing.description_sale or None,
            'color': listing.color or None,
            'material': listing.material or None,
            'is_verified_item': listing.is_verified_item,
            'image_urls': (
                ['/api/v1/image/product.template/%s' % listing.id] +
                ['/api/v1/image/product.image/%s' % img.id
                 for img in listing.product_template_image_ids]),
        })
    return data


def serialize_shop(seller, partner=None, detail=False):
    data = {
        'id': seller.id,
        'name': seller.name,
        'slug': seller.slug,
        'bio': seller.bio or None,
        'city': seller.city or None,
        'state': seller.state,
        'rating': round(seller.rating_avg, 1),
        'review_count': seller.review_count,
        'follower_count': seller.follower_count,
        'active_listing_count': seller.active_listing_count,
        'sold_count': seller.sold_listing_count,
        'is_verified': seller.kyc_status == 'verified',
        'is_following': bool(partner) and seller.is_followed_by(partner),
        'logo_url': '/api/v1/image/marketplace.seller/%s?field=logo' % seller.id,
        'banner_url': '/api/v1/image/marketplace.seller/%s?field=banner' % seller.id,
    }
    if detail:
        data.update({
            'instagram_handle': seller.instagram_handle or None,
            'whatsapp_number': seller.whatsapp_number or None,
            'created_at': dt(seller.create_date),
        })
    return data


def serialize_order(order, role='buyer'):
    listings = order._get_marketplace_listings()
    data = {
        'id': order.id,
        'name': order.name,
        'state': order.state,
        'created_at': dt(order.create_date),
        'escrow_state': order.escrow_state,
        'delivery_state': order.marketplace_delivery_state,
        'payment_method': order.marketplace_payment_method,
        'payment_received': order.payment_received,
        'buyer_confirmed_delivery': order.buyer_confirmed_delivery,
        'tracking_number': order.tracking_number or None,
        'tracking_url': order.tracking_url or None,
        'courier': order.marketplace_courier_id.name or None,
        'shipping_label_ref': order.shipping_label_ref or None,
        'shipping_label_url': (
            '/api/v1/shops/me/orders/%s/label' % order.id
            if order.shipping_label_ref else None),
        'currency_symbol': order.currency_id.symbol,
        'item_total': order.marketplace_item_total,
        'buyer_protection_fee': order.buyer_protection_fee,
        'shipping_fee': order.shipping_fee,
        'total': order.amount_total,
        'items': [{
            'id': l.id,
            'name': l.name,
            'price': l.list_price,
            'image_url': '/api/v1/image/product.template/%s' % l.id,
        } for l in listings],
        'seller': {
            'id': order.marketplace_seller_id.id,
            'name': order.marketplace_seller_id.name,
        } if order.marketplace_seller_id else None,
        'has_open_dispute': bool(order.dispute_ids.filtered(
            lambda d: d.state in ('open', 'under_review'))),
    }
    if role == 'seller':
        data.update({
            'buyer': {
                'name': order.partner_id.name,
                'city': order.partner_id.city or None,
                'street': order.partner_id.street or None,
                'phone': order.partner_id.phone or None,
            },
            'seller_payout_amount': order.seller_payout_amount,
        })
    return data


def serialize_review(review):
    return {
        'id': review.id,
        'rating': int(review.rating),
        'comment': review.comment or None,
        'reviewer': review.reviewer_id.name,
        'created_at': dt(review.create_date),
    }


def serialize_thread(thread, partner):
    last = thread.message_ids[-1:] if thread.message_ids else None
    return {
        'id': thread.id,
        'subject': thread.display_subject,
        'listing_id': thread.listing_id.id or None,
        'listing_name': thread.listing_id.name or None,
        'listing_image_url': (
            '/api/v1/image/product.template/%s' % thread.listing_id.id
            if thread.listing_id else None),
        'seller_id': thread.seller_id.id,
        'seller_name': thread.seller_id.name,
        'buyer_name': thread.buyer_partner_id.name,
        'i_am_seller': thread.seller_id.partner_id == partner,
        'unread_count': thread.unread_count(partner),
        'last_message': last.body if last else None,
        'last_message_at': dt(thread.last_message_date),
    }


def serialize_message(message, partner):
    return {
        'id': message.id,
        'body': message.body,
        'author': message.author_partner_id.name,
        'mine': message.author_partner_id == partner,
        'created_at': dt(message.create_date),
    }


class MarketplaceApiBase(http.Controller):
    """Utility endpoints: health check + authenticated image proxy."""

    @http.route(API + '/ping', type='http', auth='none', methods=['GET'],
                csrf=False)
    def ping(self, **kw):
        return json_response({'status': 'ok', 'version': 'v1'})

    IMAGE_WHITELIST = {
        'product.template': 'image_1024',
        'product.image': 'image_1024',
        'marketplace.seller': 'logo',
    }

    @http.route(API + '/image/<string:model>/<int:rid>', type='http',
                auth='public', methods=['GET'], csrf=False)
    def api_image(self, model, rid, field=None, **kw):
        """Serve images to the mobile app.

        Public listings are served to anyone; unpublished records only to
        their owner (via Bearer token).
        """
        if model not in self.IMAGE_WHITELIST:
            return request.not_found()
        default_field = self.IMAGE_WHITELIST[model]
        field = field if field in ('logo', 'banner', 'image_1024',
                                   'image_512', 'image_256') else default_field
        record = request.env[model].sudo().browse(rid)
        if not record.exists():
            return request.not_found()

        user = get_auth_user()
        partner = user.partner_id if user else None
        allowed = False
        if model == 'product.template':
            allowed = record.listing_state in ('active', 'reserved', 'sold')
            if not allowed and partner:
                allowed = record.marketplace_seller_id.partner_id == partner
        elif model == 'product.image':
            tmpl = record.product_tmpl_id
            allowed = tmpl.listing_state in ('active', 'reserved', 'sold')
            if not allowed and partner:
                allowed = tmpl.marketplace_seller_id.partner_id == partner
        elif model == 'marketplace.seller':
            allowed = True
        if not allowed:
            return request.not_found()

        return request.env['ir.binary']._get_image_stream_from(
            record, field).get_response()
