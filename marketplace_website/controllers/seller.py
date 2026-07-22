# -*- coding: utf-8 -*-
import base64

from odoo import http, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

from .main import MarketplaceMain


class MarketplaceSeller(MarketplaceMain):

    def _seller(self):
        """Current user's shop (may be empty recordset)."""
        return request.env['marketplace.seller'].sudo().search(
            [('partner_id', '=', self._partner().id)], limit=1)

    def _seller_required(self):
        seller = self._seller()
        if not seller:
            return None
        return seller

    # ==================================================================
    # Start selling / create shop
    # ==================================================================
    @http.route('/market/sell', type='http', auth='public', website=True,
                sitemap=True)
    def market_sell(self, **kw):
        if not self._is_logged():
            return request.redirect('/web/login?redirect=/market/sell')
        seller = self._seller()
        if seller:
            return request.redirect('/market/dashboard')
        values = self._base_values()
        values['error'] = kw.get('error')
        return request.render('marketplace_website.market_shop_create', values)

    @http.route('/market/sell/create', type='http', auth='user',
                methods=['POST'], website=True)
    def market_sell_create(self, **post):
        if self._seller():
            return request.redirect('/market/dashboard')
        name = (post.get('shop_name') or '').strip()
        if not name:
            return request.redirect(
                '/market/sell?error=%s' % _('Please choose a shop name.'))
        Seller = request.env['marketplace.seller'].sudo()
        try:
            seller = Seller.create({
                'name': name,
                'slug': Seller._slugify(name),
                'partner_id': self._partner().id,
                'bio': post.get('bio') or False,
                'city': post.get('city') or False,
                'instagram_handle': post.get('instagram_handle') or False,
                'whatsapp_number': post.get('whatsapp_number') or False,
                'state': 'approved',  # instant onboarding; KYC gates payouts
            })
        except ValidationError as e:
            return request.redirect('/market/sell?error=%s' % str(e))
        logo = request.httprequest.files.get('logo')
        if logo and logo.filename:
            seller.logo = base64.b64encode(logo.read())
        return request.redirect('/market/dashboard')

    # ==================================================================
    # Dashboard home
    # ==================================================================
    @http.route('/market/dashboard', type='http', auth='user', website=True,
                sitemap=False)
    def dashboard(self, **kw):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        orders = seller.order_ids.filtered(lambda o: o.state == 'sale')
        to_ship = orders.filtered(
            lambda o: o.marketplace_delivery_state == 'pending')
        values = self._base_values()
        values.update({
            'seller': seller,
            'orders_to_ship': to_ship,
            'recent_orders': orders[:5],
            'recent_reviews': seller.review_ids.filtered(
                lambda r: r.state == 'published')[:5],
            'analytics': seller.get_sales_analytics(),
        })
        return request.render('marketplace_website.dashboard_home', values)

    # ==================================================================
    # Listings management
    # ==================================================================
    @http.route('/market/dashboard/listings', type='http', auth='user',
                website=True, sitemap=False)
    def dashboard_listings(self, state=None, **kw):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        listings = seller.listing_ids
        if state:
            listings = listings.filtered(lambda l: l.listing_state == state)
        values = self._base_values()
        values.update({
            'seller': seller,
            'listings': listings.sorted('create_date', reverse=True),
            'state_filter': state,
        })
        return request.render('marketplace_website.dashboard_listings', values)

    @http.route('/market/dashboard/listings/new', type='http', auth='user',
                website=True, sitemap=False)
    def dashboard_listing_new(self, **kw):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        values = self._base_values()
        values.update(self._listing_form_values(seller))
        values['error'] = kw.get('error')
        return request.render('marketplace_website.dashboard_listing_form', values)

    @http.route('/market/dashboard/listings/<int:listing_id>/edit',
                type='http', auth='user', website=True, sitemap=False)
    def dashboard_listing_edit(self, listing_id, **kw):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        listing = self._own_listing_or_404(seller, listing_id)
        values = self._base_values()
        values.update(self._listing_form_values(seller))
        values['listing'] = listing
        values['error'] = kw.get('error')
        return request.render('marketplace_website.dashboard_listing_form', values)

    def _listing_form_values(self, seller):
        env = request.env
        return {
            'seller': seller,
            'brands': env['marketplace.brand'].sudo().search([]),
            'sizes': env['marketplace.size'].sudo().search([]),
            'all_categories': env['product.public.category'].sudo().search([]),
            'conditions': env['product.template']._fields['condition'].selection,
        }

    def _own_listing_or_404(self, seller, listing_id):
        listing = request.env['product.template'].sudo().browse(listing_id)
        if not listing.exists() or listing.marketplace_seller_id != seller:
            raise request.not_found()
        return listing

    @http.route('/market/dashboard/listings/save', type='http', auth='user',
                methods=['POST'], website=True)
    def dashboard_listing_save(self, **post):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        listing_id = int(post.get('listing_id') or 0)
        name = (post.get('name') or '').strip()
        back = ('/market/dashboard/listings/%s/edit' % listing_id
                if listing_id else '/market/dashboard/listings/new')
        if not name:
            return request.redirect(
                '%s?error=%s' % (back, _('Title is required.')))
        try:
            price = float(post.get('price') or 0)
        except ValueError:
            price = 0
        if price <= 0:
            return request.redirect(
                '%s?error=%s' % (back, _('Please set a valid price.')))

        try:
            stock_quantity = int(post.get('stock_quantity') or 1)
        except ValueError:
            stock_quantity = 1
        if stock_quantity <= 0:
            return request.redirect(
                '%s?error=%s' % (back, _(
                    'Please set how many you have in stock.')))

        vals = {
            'name': name,
            'list_price': price,
            'stock_quantity': stock_quantity,
            'description_sale': post.get('description') or False,
            'condition': post.get('condition') or False,
            'listing_color': post.get('listing_color') or False,
            'material': post.get('material') or False,
            'type': 'consu',
        }
        brand_name = (post.get('brand_name') or '').strip()
        if brand_name:
            brand = request.env['marketplace.brand'].get_or_create_by_name(
                brand_name)
            vals['marketplace_brand_id'] = brand.id
        size_name = (post.get('size_name') or '').strip()
        if size_name:
            size = request.env['marketplace.size'].get_or_create(
                size_name, post.get('size_category'))
            vals['marketplace_size_id'] = size.id
        if post.get('category_id'):
            vals['public_categ_ids'] = [(6, 0, [int(post['category_id'])])]
        if post.get('original_price'):
            try:
                vals['original_price'] = float(post['original_price'])
            except ValueError:
                pass

        Product = request.env['product.template'].sudo()
        if listing_id:
            listing = self._own_listing_or_404(seller, listing_id)
            listing.write(vals)
        else:
            vals.update({
                'is_marketplace_listing': True,
                'marketplace_seller_id': seller.id,
                'listing_state': 'draft',
                'sale_ok': True,
            })
            listing = Product.create(vals)

        # Photos: first new photo becomes the cover if none is set
        files = request.httprequest.files.getlist('images')
        for f in files:
            if not f or not f.filename:
                continue
            data = base64.b64encode(f.read())
            if not listing.image_1920:
                listing.image_1920 = data
            else:
                request.env['product.image'].sudo().create({
                    'product_tmpl_id': listing.id,
                    'name': f.filename,
                    'image_1920': data,
                })

        # Remove extra images ticked for deletion
        remove_ids = request.httprequest.form.getlist('remove_image_ids')
        if remove_ids:
            imgs = request.env['product.image'].sudo().browse(
                [int(i) for i in remove_ids if i.isdigit()])
            imgs.filtered(
                lambda i: i.product_tmpl_id == listing).unlink()

        if post.get('action') == 'publish':
            try:
                listing.action_submit_listing()
            except UserError as e:
                return request.redirect(
                    '/market/dashboard/listings/%s/edit?error=%s'
                    % (listing.id, str(e)))
        return request.redirect('/market/dashboard/listings')

    @http.route('/market/dashboard/listings/<int:listing_id>/<string:action>',
                type='http', auth='user', methods=['POST'], website=True)
    def dashboard_listing_action(self, listing_id, action, **kw):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        listing = self._own_listing_or_404(seller, listing_id)
        try:
            if action == 'publish':
                listing.action_submit_listing()
            elif action == 'remove':
                listing.action_remove_listing()
            elif action == 'relist':
                listing.action_relist()
            elif action == 'delete':
                listing.action_delete_listing()
        except UserError as e:
            return request.redirect(
                '/market/dashboard/listings?error=%s' % str(e))
        return request.redirect('/market/dashboard/listings')

    # ==================================================================
    # Seller orders
    # ==================================================================
    @http.route('/market/dashboard/orders', type='http', auth='user',
                website=True, sitemap=False)
    def dashboard_orders(self, **kw):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        orders = request.env['sale.order'].sudo().search([
            ('marketplace_seller_id', '=', seller.id),
            ('state', '=', 'sale'),
        ], order='create_date desc')
        values = self._base_values()
        values.update({
            'seller': seller,
            'orders': orders,
            'couriers': request.env['marketplace.courier'].sudo().search([]),
            'error': kw.get('error'),
        })
        return request.render('marketplace_website.dashboard_orders', values)

    @http.route('/market/dashboard/orders/<int:order_id>/ship', type='http',
                auth='user', methods=['POST'], website=True)
    def dashboard_order_ship(self, order_id, courier_id=None,
                             tracking_number=None, **kw):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.marketplace_seller_id != seller:
            raise request.not_found()
        try:
            order.action_mark_shipped(
                tracking_number=tracking_number, courier_id=courier_id)
            template = request.env.ref(
                'marketplace_core.mail_template_order_shipped',
                raise_if_not_found=False)
            if template:
                template.sudo().send_mail(order.id)
        except UserError as e:
            return request.redirect(
                '/market/dashboard/orders?error=%s' % str(e))
        return request.redirect('/market/dashboard/orders')

    @http.route('/market/dashboard/orders/<int:order_id>/label', type='http',
                auth='user', website=True, sitemap=False)
    def dashboard_order_label(self, order_id, **kw):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.marketplace_seller_id != seller:
            raise request.not_found()
        if not order.shipping_label_ref:
            return request.redirect('/market/dashboard/orders')
        attachment = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'sale.order'), ('res_id', '=', order.id),
            ('name', '=', 'shipping-label-%s.pdf' % order.name)], limit=1)
        if not attachment:
            return request.redirect('/market/dashboard/orders')
        return request.make_response(
            base64.b64decode(attachment.datas),
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition',
                 'inline; filename="%s"' % attachment.name),
            ])

    # ==================================================================
    # Wallet & payouts
    # ==================================================================
    @http.route('/market/dashboard/wallet', type='http', auth='user',
                website=True, sitemap=False)
    def dashboard_wallet(self, **kw):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        values = self._base_values()
        values.update({
            'seller': seller,
            'transactions': seller.wallet_transaction_ids,
            'payouts': seller.payout_ids,
            'error': kw.get('error'),
        })
        return request.render('marketplace_website.dashboard_wallet', values)

    @http.route('/market/dashboard/wallet/payout', type='http', auth='user',
                methods=['POST'], website=True)
    def dashboard_request_payout(self, amount=None, **kw):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        try:
            request.env['marketplace.seller.payout'].request_payout(
                seller, amount or 0)
        except (UserError, ValueError) as e:
            return request.redirect(
                '/market/dashboard/wallet?error=%s' % str(e))
        return request.redirect('/market/dashboard/wallet')

    # ==================================================================
    # Shop settings & KYC
    # ==================================================================
    @http.route('/market/dashboard/settings', type='http', auth='user',
                website=True, sitemap=False)
    def dashboard_settings(self, **kw):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        values = self._base_values()
        values.update({
            'seller': seller,
            'error': kw.get('error'),
            'saved': kw.get('saved'),
        })
        return request.render('marketplace_website.dashboard_settings', values)

    @http.route('/market/dashboard/settings/save', type='http', auth='user',
                methods=['POST'], website=True)
    def dashboard_settings_save(self, **post):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        vals = {}
        for field in ('name', 'bio', 'city', 'instagram_handle',
                      'whatsapp_number'):
            if post.get(field) is not None:
                vals[field] = post.get(field) or False
        if not vals.get('name'):
            vals.pop('name', None)
        seller.write(vals)
        logo = request.httprequest.files.get('logo')
        if logo and logo.filename:
            seller.logo = base64.b64encode(logo.read())
        banner = request.httprequest.files.get('banner')
        if banner and banner.filename:
            seller.banner = base64.b64encode(banner.read())
        return request.redirect('/market/dashboard/settings?saved=1')

    @http.route('/market/dashboard/settings/payout', type='http', auth='user',
                methods=['POST'], website=True)
    def dashboard_payout_save(self, **post):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        seller.write({
            'payout_method': post.get('payout_method') or 'bank',
            'bank_name': post.get('bank_name') or False,
            'bank_account_title': post.get('bank_account_title') or False,
            'bank_account_number': post.get('bank_account_number') or False,
            'mobile_wallet_number': post.get('mobile_wallet_number') or False,
        })
        return request.redirect('/market/dashboard/settings?saved=1')

    @http.route('/market/dashboard/settings/kyc', type='http', auth='user',
                methods=['POST'], website=True)
    def dashboard_kyc_save(self, **post):
        seller = self._seller_required()
        if not seller:
            return request.redirect('/market/sell')
        vals = {
            'kyc_id_type': post.get('kyc_id_type') or False,
            'kyc_id_number': post.get('kyc_id_number') or False,
        }
        seller.write(vals)
        files = request.httprequest.files.getlist('kyc_documents')
        attachment_ids = []
        for f in files:
            if not f or not f.filename:
                continue
            attachment = request.env['ir.attachment'].sudo().create({
                'name': f.filename,
                'datas': base64.b64encode(f.read()),
                'res_model': 'marketplace.seller',
                'res_id': seller.id,
            })
            attachment_ids.append(attachment.id)
        if attachment_ids:
            seller.write({'kyc_document_ids': [(4, i) for i in attachment_ids]})
        try:
            seller.action_submit_kyc()
        except UserError as e:
            return request.redirect(
                '/market/dashboard/settings?error=%s' % str(e))
        return request.redirect('/market/dashboard/settings?saved=1')
