# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request

from .base import (API, api_endpoint, get_json_body, json_response,
                   serialize_listing)

PAGE_SIZE = 20


class MarketplaceApiCatalog(http.Controller):

    # ------------------------------------------------------------------
    # Reference data
    # ------------------------------------------------------------------
    @http.route(API + '/meta', type='http', auth='public', methods=['GET'],
                csrf=False)
    @api_endpoint(auth_required=False)
    def meta(self, api_user=None, **kw):
        env = request.env
        return json_response({
            'categories': [{
                'id': c.id,
                'name': c.name,
                'parent_id': c.parent_id.id or None,
            } for c in env['product.public.category'].sudo().search([])],
            'brands': [{
                'id': b.id, 'name': b.name, 'is_luxury': b.is_luxury,
            } for b in env['marketplace.brand'].sudo().search([])],
            'sizes': [{
                'id': s.id, 'name': s.name, 'category': s.category,
            } for s in env['marketplace.size'].sudo().search([])],
            'conditions': [
                {'value': value, 'label': label}
                for value, label in
                env['product.template']._fields['condition'].selection],
            'couriers': [{
                'id': c.id, 'name': c.name, 'supports_cod': c.supports_cod,
                'flat_rate': c.flat_rate,
            } for c in env['marketplace.courier'].sudo().search([])],
            'payment_methods': [
                {'value': value, 'label': label}
                for value, label in
                env['sale.order']._fields['marketplace_payment_method'].selection],
            'stripe_configured':
                env['marketplace.cart.item'].sudo().stripe_configured(),
        })

    # ------------------------------------------------------------------
    # Listings: search & detail
    # ------------------------------------------------------------------
    @http.route(API + '/listings', type='http', auth='public',
                methods=['GET'], csrf=False)
    @api_endpoint(auth_required=False)
    def listings(self, api_user=None, page='1', **kw):
        Product = request.env['product.template'].sudo()
        domain = Product.marketplace_search_domain(kw)
        order = Product.marketplace_sort_order(kw.get('sort'))
        page = max(1, int(page) if str(page).isdigit() else 1)
        total = Product.search_count(domain)
        records = Product.search(domain, order=order, limit=PAGE_SIZE,
                                 offset=(page - 1) * PAGE_SIZE)
        partner = api_user.partner_id if api_user else None
        return json_response({
            'items': [serialize_listing(rec, partner) for rec in records],
            'page': page,
            'page_size': PAGE_SIZE,
            'total': total,
        })

    @http.route(API + '/listings/<int:listing_id>', type='http',
                auth='public', methods=['GET'], csrf=False)
    @api_endpoint(auth_required=False)
    def listing_detail(self, listing_id, api_user=None, **kw):
        listing = self._get_visible_listing(listing_id, api_user)
        listing.increment_view()
        partner = api_user.partner_id if api_user else None
        return json_response(serialize_listing(listing, partner, detail=True))

    def _get_visible_listing(self, listing_id, api_user):
        listing = request.env['product.template'].sudo().browse(listing_id)
        if not listing.exists() or not listing.is_marketplace_listing:
            raise request.not_found()
        partner = api_user.partner_id if api_user else None
        is_owner = (partner and
                    listing.marketplace_seller_id.partner_id == partner)
        if listing.listing_state not in ('active', 'reserved', 'sold') \
                and not is_owner:
            raise request.not_found()
        return listing

    # ------------------------------------------------------------------
    # Listings: seller CRUD
    # ------------------------------------------------------------------
    def _own_seller(self, api_user):
        seller = api_user.partner_id.sudo().get_marketplace_seller()
        if not seller or seller.state != 'approved':
            return None
        return seller

    @http.route(API + '/listings', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def listing_create(self, api_user=None, **kw):
        seller = self._own_seller(api_user)
        if not seller:
            return json_response(
                error='You need an approved shop before you can list items.',
                status=403, error_code='not_approved')
        body = get_json_body()
        vals, error = self._listing_vals(body, require_all=True)
        if error:
            return json_response(error=error, status=400,
                                 error_code='validation')
        vals.update({
            'is_marketplace_listing': True,
            'marketplace_seller_id': seller.id,
            'listing_state': 'draft',
            'type': 'consu',
            'sale_ok': True,
        })
        listing = request.env['product.template'].sudo().create(vals)
        self._apply_images(listing, body.get('images') or [])
        if body.get('video') is not None:
            self._apply_video(listing, body.get('video'),
                              body.get('video_filename'))
        if body.get('publish', True):
            listing.action_submit_listing()
        return json_response(
            serialize_listing(listing, api_user.partner_id, detail=True),
            status=201)

    @http.route(API + '/listings/<int:listing_id>', type='http',
                auth='public', methods=['PUT', 'PATCH'], csrf=False)
    @api_endpoint(auth_required=True)
    def listing_update(self, listing_id, api_user=None, **kw):
        listing = self._own_listing(listing_id, api_user)
        body = get_json_body()
        vals, error = self._listing_vals(body, require_all=False)
        if error:
            return json_response(error=error, status=400,
                                 error_code='validation')
        if vals:
            listing.write(vals)
        if body.get('images') is not None:
            listing.write({'image_1920': False})
            listing.product_template_image_ids.unlink()
            self._apply_images(listing, body.get('images') or [])
        if 'video' in body:
            self._apply_video(listing, body.get('video'),
                              body.get('video_filename'))
        action = body.get('action')
        if action == 'publish':
            listing.action_submit_listing()
        elif action == 'remove':
            listing.action_remove_listing()
        elif action == 'relist':
            listing.action_relist()
        return json_response(serialize_listing(
            listing, api_user.partner_id, detail=True))

    @http.route(API + '/listings/<int:listing_id>', type='http',
                auth='public', methods=['DELETE'], csrf=False)
    @api_endpoint(auth_required=True)
    def listing_delete(self, listing_id, api_user=None, **kw):
        listing = self._own_listing(listing_id, api_user)
        listing.action_delete_listing()
        return json_response({'deleted': True})

    def _own_listing(self, listing_id, api_user):
        listing = request.env['product.template'].sudo().browse(listing_id)
        if not listing.exists() or \
                listing.marketplace_seller_id.partner_id != api_user.partner_id:
            raise request.not_found()
        return listing

    def _listing_vals(self, body, require_all=True):
        vals = {}
        if 'name' in body or require_all:
            name = (body.get('name') or '').strip()
            if not name:
                return None, 'Title is required.'
            vals['name'] = name
        if 'original_price' in body:
            try:
                vals['original_price'] = float(body.get('original_price') or 0)
            except (TypeError, ValueError):
                pass
        if 'discount_pct' in body:
            try:
                vals['discount_pct'] = float(body.get('discount_pct') or 0)
            except (TypeError, ValueError):
                pass
        has_discount_calc = bool(
            vals.get('original_price') and vals.get('discount_pct'))
        if 'price' in body or require_all:
            try:
                price = float(body.get('price') or 0)
            except (TypeError, ValueError):
                price = 0
            if price <= 0 and has_discount_calc:
                price = round(
                    vals['original_price'] * (1 - vals['discount_pct'] / 100.0), 2)
            if price <= 0:
                return None, 'A positive price is required.'
            vals['list_price'] = price
        if 'stock_quantity' in body:
            try:
                qty = int(body.get('stock_quantity') or 1)
            except (TypeError, ValueError):
                qty = 1
            if qty <= 0:
                return None, 'Quantity available must be at least 1.'
            vals['stock_quantity'] = qty
        elif require_all:
            vals['stock_quantity'] = 1
        if 'description' in body:
            vals['description_sale'] = body.get('description') or False
        if 'condition' in body:
            vals['condition'] = body.get('condition') or False
        if (body.get('brand_name') or '').strip():
            brand = request.env['marketplace.brand'].get_or_create_by_name(
                body['brand_name'])
            vals['marketplace_brand_id'] = brand.id
        elif 'brand_id' in body:
            vals['marketplace_brand_id'] = (
                int(body['brand_id']) if body.get('brand_id') else False)
        if (body.get('size_name') or '').strip():
            size = request.env['marketplace.size'].get_or_create(
                body['size_name'], body.get('size_category'))
            vals['marketplace_size_id'] = size.id
        elif 'size_id' in body:
            vals['marketplace_size_id'] = (
                int(body['size_id']) if body.get('size_id') else False)
        if 'category_id' in body:
            vals['public_categ_ids'] = (
                [(6, 0, [int(body['category_id'])])]
                if body.get('category_id') else [(5, 0, 0)])
        if 'color' in body:
            vals['color'] = body.get('color') or False
        if 'material' in body:
            vals['material'] = body.get('material') or False
        return vals, None

    def _apply_images(self, listing, images_b64):
        """images_b64: list of base64-encoded image payloads."""
        for index, img in enumerate(images_b64[:8]):
            if not img:
                continue
            # Tolerate data-URI prefixes from mobile clients
            if ',' in img[:64] and img.strip().startswith('data:'):
                img = img.split(',', 1)[1]
            try:
                data = img.encode('ascii')
                base64.b64decode(data, validate=True)
            except Exception:
                continue
            if index == 0 and not listing.image_1920:
                listing.image_1920 = data
            else:
                request.env['product.image'].sudo().create({
                    'product_tmpl_id': listing.id,
                    'name': '%s-%s' % (listing.name, index),
                    'image_1920': data,
                })

    def _apply_video(self, listing, video_b64, filename=None):
        """video_b64: a single base64-encoded video payload, or falsy to
        clear the listing's video."""
        if not video_b64:
            listing.write({'video': False, 'video_filename': False})
            return
        if ',' in video_b64[:64] and video_b64.strip().startswith('data:'):
            video_b64 = video_b64.split(',', 1)[1]
        try:
            data = video_b64.encode('ascii')
            base64.b64decode(data, validate=True)
        except Exception:
            return
        listing.write({
            'video': data,
            'video_filename': filename or 'video.mp4',
        })

    # ------------------------------------------------------------------
    # Favourites
    # ------------------------------------------------------------------
    @http.route(API + '/favorites', type='http', auth='public',
                methods=['GET'], csrf=False)
    @api_endpoint(auth_required=True)
    def favorites(self, api_user=None, **kw):
        partner = api_user.partner_id
        listings = partner.sudo().marketplace_favorite_ids.filtered(
            lambda l: l.listing_state in ('active', 'reserved', 'sold'))
        return json_response({
            'items': [serialize_listing(rec, partner) for rec in listings],
        })

    @http.route(API + '/listings/<int:listing_id>/favorite', type='http',
                auth='public', methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def toggle_favorite(self, listing_id, api_user=None, **kw):
        listing = self._get_visible_listing(listing_id, api_user)
        state = listing.action_toggle_favorite(api_user.partner_id)
        return json_response({
            'is_favorite': state,
            'favorite_count': listing.favorite_count,
        })
