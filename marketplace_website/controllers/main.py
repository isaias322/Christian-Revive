# -*- coding: utf-8 -*-
import base64

from odoo import http, fields, _
from odoo.exceptions import UserError
from odoo.http import request

PAGE_SIZE = 24


class MarketplaceMain(http.Controller):

    # ==================================================================
    # Helpers
    # ==================================================================
    def _partner(self):
        return request.env.user.partner_id

    def _is_logged(self):
        return not request.env.user._is_public()

    def _base_values(self):
        env = request.env
        partner = self._partner()
        cart_count = 0
        unread = 0
        if self._is_logged():
            cart_count = env['marketplace.cart.item'].sudo().search_count(
                [('partner_id', '=', partner.id)])
            threads = env['marketplace.thread'].sudo().search([
                '|', ('buyer_partner_id', '=', partner.id),
                ('seller_id.partner_id', '=', partner.id)])
            unread = sum(t.unread_count(partner) for t in threads)
        return {
            'is_logged': self._is_logged(),
            'mk_partner': partner,
            'mk_cart_count': cart_count,
            'mk_unread_count': unread,
            'mk_categories': env['product.public.category'].sudo().search(
                [('parent_id', '=', False)]),
        }

    def _listing_or_404(self, listing_id, published_only=True):
        listing = request.env['product.template'].sudo().browse(listing_id)
        if not listing.exists() or not listing.is_marketplace_listing:
            raise request.not_found()
        if published_only and listing.listing_state not in (
                'active', 'reserved', 'sold'):
            raise request.not_found()
        return listing

    # ==================================================================
    # Home & search
    # ==================================================================
    @http.route('/market', type='http', auth='public', website=True, sitemap=True)
    def market_home(self, **kw):
        env = request.env
        Product = env['product.template'].sudo()
        base_domain = Product.marketplace_search_domain()
        newest = Product.search(
            base_domain, order=Product.marketplace_sort_order('newest'),
            limit=12)
        popular = Product.search(
            base_domain, order=Product.marketplace_sort_order('popular'),
            limit=8)
        featured_shops = env['marketplace.seller'].sudo().search([
            ('state', '=', 'approved'), ('is_featured', '=', True)], limit=6)
        if not featured_shops:
            featured_shops = env['marketplace.seller'].sudo().search(
                [('state', '=', 'approved')], limit=6)
        following = Product.browse()
        if self._is_logged():
            followed = self._partner().marketplace_followed_shop_ids
            if followed:
                following = Product.search(
                    base_domain + [('marketplace_seller_id', 'in', followed.ids)],
                    order='create_date desc', limit=8)
        values = self._base_values()
        values.update({
            'newest': newest,
            'popular': popular,
            'featured_shops': featured_shops,
            'following': following,
        })
        return request.render('marketplace_website.market_home', values)

    @http.route('/market/search', type='http', auth='public', website=True,
                sitemap=False)
    def market_search(self, page=1, **kw):
        env = request.env
        Product = env['product.template'].sudo()
        filters = {k: v for k, v in kw.items() if v}
        domain = Product.marketplace_search_domain(filters)
        order = Product.marketplace_sort_order(kw.get('sort'))
        total = Product.search_count(domain)
        page = max(1, int(page))
        listings = Product.search(
            domain, order=order, limit=PAGE_SIZE,
            offset=(page - 1) * PAGE_SIZE)
        values = self._base_values()
        values.update({
            'listings': listings,
            'total': total,
            'page': page,
            'page_count': max(1, -(-total // PAGE_SIZE)),
            'filters': kw,
            'brands': env['marketplace.brand'].sudo().search([]),
            'sizes': env['marketplace.size'].sudo().search([]),
            'all_categories': env['product.public.category'].sudo().search([]),
            'conditions': env['product.template']._fields['condition'].selection,
        })
        return request.render('marketplace_website.market_search', values)

    # ==================================================================
    # Item page
    # ==================================================================
    @http.route('/market/item/<int:listing_id>', type='http', auth='public',
                website=True, sitemap=False)
    def market_item(self, listing_id, **kw):
        listing = self._listing_or_404(listing_id)
        listing.increment_view()
        partner = self._partner()
        seller = listing.marketplace_seller_id
        similar = request.env['product.template'].sudo().search(
            request.env['product.template'].marketplace_search_domain({
                'category_id': listing.public_categ_ids[:1].id
                if listing.public_categ_ids else None,
            }) + [('id', '!=', listing.id)],
            limit=8, order='create_date desc')
        reviews = request.env['marketplace.review'].sudo().search([
            ('seller_id', '=', seller.id), ('state', '=', 'published')],
            limit=5)
        values = self._base_values()
        values.update({
            'listing': listing,
            'seller': seller,
            'similar': similar,
            'reviews': reviews,
            'is_favorite': self._is_logged() and listing.is_favorited_by(partner),
            'is_own': self._is_logged() and seller.partner_id == partner,
        })
        return request.render('marketplace_website.market_item', values)

    @http.route('/market/item/<int:listing_id>/favorite', type='http',
                auth='user', methods=['POST'], csrf=False, website=True)
    def market_toggle_favorite(self, listing_id, **kw):
        listing = self._listing_or_404(listing_id)
        state = listing.action_toggle_favorite(self._partner())
        return request.make_json_response({
            'favorite': state, 'count': listing.favorite_count})

    # ==================================================================
    # Email verification
    # ==================================================================
    @http.route('/market/verify-email', type='http', auth='public',
                website=True, sitemap=False)
    def market_verify_email(self, token=None, **kw):
        partner = request.env['marketplace.email.verification'].sudo().verify(token)
        values = self._base_values()
        values['verified'] = bool(partner)
        return request.render('marketplace_website.market_verify_email', values)

    # ==================================================================
    # Made-to-order
    # ==================================================================
    @http.route('/market/item/<int:listing_id>/mto', type='http',
                auth='user', website=True, sitemap=False)
    def market_mto_request(self, listing_id, **kw):
        listing = self._listing_or_404(listing_id)
        if not listing.is_mto_available:
            return request.redirect('/market/item/%s' % listing_id)
        icp = request.env['ir.config_parameter'].sudo()
        deposit_pct = float(icp.get_param('marketplace_core.mto_deposit_pct', '50.0'))
        fixed = float(icp.get_param('marketplace_core.buyer_protection_fixed', '100.0'))
        pct = float(icp.get_param('marketplace_core.buyer_protection_pct', '5.0'))
        fee = fixed + listing.list_price * pct / 100.0
        order_total = listing.list_price + fee
        values = self._base_values()
        values.update({
            'listing': listing,
            'deposit_pct': deposit_pct,
            'order_total': order_total,
            'deposit_amount': round(order_total * deposit_pct / 100.0, 2),
            'couriers': request.env['marketplace.courier'].sudo().search([]),
            'stripe_configured':
                request.env['marketplace.cart.item'].stripe_configured(),
            'error': kw.get('error'),
        })
        return request.render('marketplace_website.market_mto_request', values)

    @http.route('/market/item/<int:listing_id>/mto-request', type='http',
                auth='user', methods=['POST'], website=True)
    def market_mto_request_confirm(self, listing_id, **post):
        listing = self._listing_or_404(listing_id)
        values = {
            'name': post.get('name'),
            'phone': post.get('phone'),
            'street': post.get('street'),
            'city': post.get('city'),
            'zip': post.get('zip'),
            'payment_method': post.get('payment_method'),
            'courier_id': post.get('courier_id'),
        }
        root = request.httprequest.url_root.rstrip('/')
        if post.get('payment_method') == 'card':
            try:
                url = request.env['marketplace.cart.item'].create_mto_deposit_stripe_session(
                    self._partner(), listing, values,
                    success_url=root + '/market/order/thanks',
                    cancel_url=root + '/market/item/%s/mto' % listing_id)
            except UserError as e:
                return request.redirect(
                    '/market/item/%s/mto?error=%s' % (listing_id, str(e)))
            return request.redirect(url, local=False)
        try:
            order = request.env['marketplace.cart.item'].mto_request(
                self._partner(), listing, values)
            order.action_mto_confirm_deposit_paid()
        except UserError as e:
            return request.redirect(
                '/market/item/%s/mto?error=%s' % (listing_id, str(e)))
        return request.redirect('/market/order/thanks?orders=%s' % order.id)

    @http.route('/market/order/<int:order_id>/mto/pay-balance', type='http',
                auth='user', methods=['POST'], website=True)
    def market_mto_pay_balance(self, order_id, **kw):
        order = self._buyer_order_or_404(order_id)
        if not order.is_mto_order:
            raise request.not_found()
        root = request.httprequest.url_root.rstrip('/')
        if order.marketplace_payment_method == 'card':
            try:
                url = request.env['marketplace.cart.item'].create_mto_balance_stripe_session(
                    order, success_url=root + '/market/order/thanks',
                    cancel_url=root + '/market/order/%s' % order.id)
            except UserError as e:
                return request.redirect(
                    '/market/order/%s?error=%s' % (order_id, str(e)))
            return request.redirect(url, local=False)
        order.action_mto_confirm_balance_paid()
        return request.redirect('/market/order/%s' % order_id)

    @http.route('/market/video/<int:listing_id>', type='http', auth='public',
                website=True, sitemap=False)
    def market_video(self, listing_id, **kw):
        listing = self._listing_or_404(listing_id, published_only=False)
        if not listing.video:
            raise request.not_found()
        is_owner = (self._is_logged() and
                    listing.marketplace_seller_id.partner_id == self._partner())
        if listing.listing_state not in ('active', 'reserved', 'sold') \
                and not is_owner:
            raise request.not_found()
        return request.make_response(
            base64.b64decode(listing.video),
            headers=[
                ('Content-Type', 'video/mp4'),
                ('Content-Disposition',
                 'inline; filename="%s"' % (listing.video_filename or 'video.mp4')),
            ])

    # ==================================================================
    # Shop page
    # ==================================================================
    @http.route('/market/shop/<string:slug>', type='http', auth='public',
                website=True, sitemap=False)
    def market_shop(self, slug, **kw):
        seller = request.env['marketplace.seller'].sudo().search(
            [('slug', '=', slug)], limit=1)
        if not seller or seller.state not in ('approved', 'suspended'):
            raise request.not_found()
        Product = request.env['product.template'].sudo()
        listings = Product.search(
            Product.marketplace_search_domain({'seller_id': seller.id}),
            order='create_date desc', limit=48)
        sold = Product.search([
            ('marketplace_seller_id', '=', seller.id),
            ('listing_state', '=', 'sold')], order='write_date desc', limit=8)
        reviews = request.env['marketplace.review'].sudo().search([
            ('seller_id', '=', seller.id), ('state', '=', 'published')],
            limit=10)
        values = self._base_values()
        values.update({
            'seller': seller,
            'listings': listings,
            'sold_listings': sold,
            'reviews': reviews,
            'is_following': self._is_logged() and seller.is_followed_by(
                self._partner()),
            'is_own': self._is_logged() and seller.partner_id == self._partner(),
        })
        return request.render('marketplace_website.market_shop', values)

    @http.route('/market/shop/<int:seller_id>/follow', type='http',
                auth='user', methods=['POST'], csrf=False, website=True)
    def market_toggle_follow(self, seller_id, **kw):
        seller = request.env['marketplace.seller'].sudo().browse(seller_id)
        if not seller.exists():
            raise request.not_found()
        state = seller.action_toggle_follow(self._partner())
        return request.make_json_response({
            'following': state, 'count': seller.follower_count})

    # ==================================================================
    # Favorites
    # ==================================================================
    @http.route('/market/favorites', type='http', auth='user', website=True,
                sitemap=False)
    def market_favorites(self, **kw):
        values = self._base_values()
        values['listings'] = self._partner().marketplace_favorite_ids.filtered(
            lambda l: l.listing_state in ('active', 'reserved', 'sold'))
        return request.render('marketplace_website.market_favorites', values)

    # ==================================================================
    # Cart & checkout
    # ==================================================================
    @http.route('/market/cart', type='http', auth='user', website=True,
                sitemap=False)
    def market_cart(self, **kw):
        items = request.env['marketplace.cart.item'].get_cart(self._partner())
        icp = request.env['ir.config_parameter'].sudo()
        fixed = float(icp.get_param(
            'marketplace_core.buyer_protection_fixed', '100.0'))
        pct = float(icp.get_param(
            'marketplace_core.buyer_protection_pct', '5.0'))
        subtotal = sum(items.mapped('price'))
        protection = (fixed + subtotal * pct / 100.0) if items else 0.0
        values = self._base_values()
        values.update({
            'items': items,
            'subtotal': subtotal,
            'protection_fee': protection,
            'total': subtotal + protection,
        })
        return request.render('marketplace_website.market_cart', values)

    @http.route('/market/cart/add/<int:listing_id>', type='http', auth='public',
                methods=['POST'], website=True)
    def market_cart_add(self, listing_id, **kw):
        if not self._is_logged():
            return request.redirect(
                '/web/login?redirect=/market/item/%s' % listing_id)
        listing = self._listing_or_404(listing_id)
        try:
            request.env['marketplace.cart.item'].add_item(
                self._partner(), listing)
        except UserError as e:
            return request.redirect(
                '/market/item/%s?error=%s' % (listing_id, str(e)))
        return request.redirect('/market/cart')

    @http.route('/market/cart/remove/<int:item_id>', type='http', auth='user',
                methods=['POST'], website=True)
    def market_cart_remove(self, item_id, **kw):
        item = request.env['marketplace.cart.item'].sudo().browse(item_id)
        if item.exists() and item.partner_id == self._partner():
            item.unlink()
        return request.redirect('/market/cart')

    @http.route('/market/checkout', type='http', auth='user', website=True,
                sitemap=False)
    def market_checkout(self, **kw):
        partner = self._partner()
        items = request.env['marketplace.cart.item'].get_cart(partner)
        if not items:
            return request.redirect('/market/cart')
        icp = request.env['ir.config_parameter'].sudo()
        fixed = float(icp.get_param(
            'marketplace_core.buyer_protection_fixed', '100.0'))
        pct = float(icp.get_param(
            'marketplace_core.buyer_protection_pct', '5.0'))
        subtotal = sum(items.mapped('price'))
        couriers = request.env['marketplace.courier'].sudo().search([])
        values = self._base_values()
        values.update({
            'items': items,
            'subtotal': subtotal,
            'protection_fee': fixed + subtotal * pct / 100.0,
            'couriers': couriers,
            'error': kw.get('error'),
            'stripe_configured':
                request.env['marketplace.cart.item'].stripe_configured(),
        })
        return request.render('marketplace_website.market_checkout', values)

    @http.route('/market/checkout/confirm', type='http', auth='user',
                methods=['POST'], website=True)
    def market_checkout_confirm(self, **post):
        partner = self._partner()
        values = {
            'name': post.get('name'),
            'phone': post.get('phone'),
            'street': post.get('street'),
            'city': post.get('city'),
            'zip': post.get('zip'),
            'payment_method': post.get('payment_method'),
            'courier_id': post.get('courier_id'),
        }
        if post.get('payment_method') == 'card':
            try:
                url = request.env['marketplace.cart.item'].create_stripe_session(
                    partner, values,
                    success_url=request.httprequest.url_root.rstrip('/')
                    + '/market/order/thanks',
                    cancel_url=request.httprequest.url_root.rstrip('/')
                    + '/market/checkout')
            except UserError as e:
                return request.redirect('/market/checkout?error=%s' % str(e))
            return request.redirect(url, local=False)
        try:
            orders = request.env['marketplace.cart.item'].checkout(
                partner, values)
        except UserError as e:
            return request.redirect('/market/checkout?error=%s' % str(e))
        return request.redirect(
            '/market/order/thanks?orders=%s' % ','.join(map(str, orders.ids)))

    @http.route('/market/order/thanks', type='http', auth='user', website=True,
                sitemap=False)
    def market_thanks(self, orders='', session_id=None, **kw):
        order_ids = [int(o) for o in orders.split(',') if o.isdigit()]
        records = request.env['sale.order'].sudo().browse(order_ids).filtered(
            lambda o: o.partner_id == self._partner())
        if not records and session_id:
            # Card payment: Stripe redirects here as soon as the buyer
            # finishes paying, which can be a moment before our webhook
            # has actually fulfilled the order — look for whatever this
            # buyer's most recent order is instead of failing outright.
            records = request.env['sale.order'].sudo().search([
                ('partner_id', '=', self._partner().id),
                ('is_marketplace_order', '=', True),
            ], order='create_date desc', limit=5)
        values = self._base_values()
        values['orders'] = records
        values['awaiting_stripe'] = bool(session_id) and not records
        return request.render('marketplace_website.market_thanks', values)

    # ==================================================================
    # Buyer orders
    # ==================================================================
    @http.route('/market/orders', type='http', auth='user', website=True,
                sitemap=False)
    def market_orders(self, **kw):
        orders = request.env['sale.order'].sudo().search([
            ('is_marketplace_order', '=', True),
            ('partner_id', '=', self._partner().id),
            ('state', '!=', 'cancel'),
        ], order='create_date desc')
        values = self._base_values()
        values['orders'] = orders
        return request.render('marketplace_website.market_orders', values)

    def _buyer_order_or_404(self, order_id):
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or not order.is_marketplace_order or \
                order.partner_id != self._partner():
            raise request.not_found()
        return order

    @http.route('/market/order/<int:order_id>', type='http', auth='user',
                website=True, sitemap=False)
    def market_order_detail(self, order_id, **kw):
        order = self._buyer_order_or_404(order_id)
        has_review = bool(request.env['marketplace.review'].sudo().search_count([
            ('order_id', '=', order.id),
            ('reviewer_id', '=', self._partner().id)]))
        values = self._base_values()
        values.update({
            'order': order,
            'has_review': has_review,
            'error': kw.get('error'),
        })
        return request.render('marketplace_website.market_order_detail', values)

    @http.route('/market/order/<int:order_id>/confirm-delivery', type='http',
                auth='user', methods=['POST'], website=True)
    def market_confirm_delivery(self, order_id, **kw):
        order = self._buyer_order_or_404(order_id)
        try:
            order.action_confirm_delivery()
        except UserError as e:
            return request.redirect(
                '/market/order/%s?error=%s' % (order_id, str(e)))
        return request.redirect('/market/order/%s' % order_id)

    @http.route('/market/order/<int:order_id>/dispute', type='http',
                auth='user', methods=['POST'], website=True)
    def market_open_dispute(self, order_id, reason=None, description=None, **kw):
        order = self._buyer_order_or_404(order_id)
        try:
            request.env['marketplace.dispute'].open_for_order(
                order, self._partner(), reason or 'other', description)
        except UserError as e:
            return request.redirect(
                '/market/order/%s?error=%s' % (order_id, str(e)))
        return request.redirect('/market/order/%s' % order_id)

    @http.route('/market/order/<int:order_id>/review', type='http',
                auth='user', methods=['POST'], website=True)
    def market_leave_review(self, order_id, rating=None, comment=None, **kw):
        order = self._buyer_order_or_404(order_id)
        try:
            request.env['marketplace.review'].create_for_order(
                order, self._partner(), rating or 5, comment)
        except UserError as e:
            return request.redirect(
                '/market/order/%s?error=%s' % (order_id, str(e)))
        return request.redirect('/market/order/%s' % order_id)

    # ==================================================================
    # Messaging
    # ==================================================================
    @http.route('/market/messages', type='http', auth='user', website=True,
                sitemap=False)
    def market_messages(self, **kw):
        partner = self._partner()
        threads = request.env['marketplace.thread'].sudo().search([
            '|', ('buyer_partner_id', '=', partner.id),
            ('seller_id.partner_id', '=', partner.id)])
        values = self._base_values()
        values['threads'] = threads
        return request.render('marketplace_website.market_messages', values)

    @http.route('/market/messages/start', type='http', auth='user',
                methods=['POST'], website=True)
    def market_message_start(self, seller_id=None, listing_id=None, **kw):
        seller = request.env['marketplace.seller'].sudo().browse(
            int(seller_id or 0))
        if not seller.exists():
            raise request.not_found()
        listing = None
        if listing_id:
            listing = request.env['product.template'].sudo().browse(
                int(listing_id))
            listing = listing.exists() and listing or None
        try:
            thread = request.env['marketplace.thread'].get_or_create_thread(
                self._partner(), seller, listing)
        except UserError:
            return request.redirect('/market')
        return request.redirect('/market/messages/thread/%s' % thread.id)

    def _thread_or_404(self, thread_id):
        thread = request.env['marketplace.thread'].sudo().browse(thread_id)
        if not thread.exists() or not thread.partner_can_access(self._partner()):
            raise request.not_found()
        return thread

    @http.route('/market/messages/thread/<int:thread_id>', type='http',
                auth='user', website=True, sitemap=False)
    def market_thread(self, thread_id, **kw):
        thread = self._thread_or_404(thread_id)
        thread.mark_read(self._partner())
        values = self._base_values()
        values['thread'] = thread
        return request.render('marketplace_website.market_thread', values)

    @http.route('/market/messages/thread/<int:thread_id>/send', type='http',
                auth='user', methods=['POST'], website=True)
    def market_thread_send(self, thread_id, body=None, **kw):
        thread = self._thread_or_404(thread_id)
        if body and body.strip():
            thread.post_message(self._partner(), body)
        return request.redirect('/market/messages/thread/%s' % thread_id)

    @http.route('/market/messages/thread/<int:thread_id>/poll', type='http',
                auth='user', website=True, sitemap=False)
    def market_thread_poll(self, thread_id, after=0, **kw):
        thread = self._thread_or_404(thread_id)
        messages = thread.message_ids.filtered(lambda m: m.id > int(after))
        thread.mark_read(self._partner())
        return request.make_json_response([{
            'id': m.id,
            'body': m.body,
            'author': m.author_partner_id.name,
            'mine': m.author_partner_id == self._partner(),
            'date': fields.Datetime.to_string(m.create_date),
            'image_url': ('/market/chat-image/%s' % m.id if m.image else None),
            'video_url': ('/market/chat-video/%s' % m.id if m.video else None),
        } for m in messages])

    @http.route('/market/chat-image/<int:message_id>', type='http',
                auth='user', website=True, sitemap=False)
    def market_chat_image(self, message_id, **kw):
        message = request.env['marketplace.thread.message'].sudo().browse(
            message_id)
        if not message.exists() or not message.image \
                or not message.thread_id.partner_can_access(self._partner()):
            raise request.not_found()
        return request.make_response(
            base64.b64decode(message.image),
            headers=[
                ('Content-Type', 'image/jpeg'),
                ('Content-Disposition',
                 'inline; filename="%s"' % (message.image_filename or 'photo.jpg')),
            ])

    @http.route('/market/chat-video/<int:message_id>', type='http',
                auth='user', website=True, sitemap=False)
    def market_chat_video(self, message_id, **kw):
        message = request.env['marketplace.thread.message'].sudo().browse(
            message_id)
        if not message.exists() or not message.video \
                or not message.thread_id.partner_can_access(self._partner()):
            raise request.not_found()
        return request.make_response(
            base64.b64decode(message.video),
            headers=[
                ('Content-Type', 'video/mp4'),
                ('Content-Disposition',
                 'inline; filename="%s"' % (message.video_filename or 'video.mp4')),
            ])
