# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.cart import Cart


class LifestyleWebsite(http.Controller):

    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def homepage(self, **kwargs):
        homepage_slides = request.env['ir.ui.view'].browse()
        homepage_sections = request.env['ir.ui.view'].browse()
        homepage_top_sections = request.env['ir.ui.view'].browse()
        homepage_main_sections = request.env['ir.ui.view'].browse()
        homepage_bottom_sections = request.env['ir.ui.view'].browse()
        featured_section = request.env['ir.ui.view'].browse()
        process_section = request.env['ir.ui.view'].browse()
        cta_section = request.env['ir.ui.view'].browse()
        process_items = request.env['ir.ui.view'].browse()
        cta_items = request.env['ir.ui.view'].browse()
        homepage_section_items_by_section = {}
        featured_products_by_section = {}

        if request.env.registry.get('lifestyle.homepage.slide'):
            homepage_slides = request.env['lifestyle.homepage.slide'].sudo().search([
                ('active', '=', True),
            ], order='sequence, id')

        featured_limit = 4
        homepage_sections_ready = bool(request.env.registry.get('lifestyle.homepage.section'))
        if homepage_sections_ready:
            homepage_sections = request.env['lifestyle.homepage.section'].sudo().search([
                ('active', '=', True),
            ], order='sequence, id')
            homepage_top_sections = homepage_sections.filtered(lambda section: section.placement == 'before_hero')
            homepage_main_sections = homepage_sections.filtered(lambda section: not section.placement or section.placement == 'main')
            homepage_bottom_sections = homepage_sections.filtered(lambda section: section.placement == 'before_footer')
            featured_sections = homepage_sections.filtered(lambda section: section.section_key == 'featured')
            featured_section = featured_sections[:1]
            process_section = homepage_sections.filtered(lambda section: section.section_key == 'process')[:1]
            cta_section = homepage_sections.filtered(lambda section: section.section_key == 'cta')[:1]
            if featured_sections:
                featured_limit = max(1, min(max(featured_sections.mapped('product_limit') or [4]), 12))
            for section in homepage_sections:
                homepage_section_items_by_section[section.id] = section.item_ids.filtered(lambda item: item.active).sorted('sequence')
            for section in featured_sections:
                section_limit = max(1, min(section.product_limit or 4, 12))
                featured_products_by_section[section.id] = request.env['product.template'].sudo().search([
                    ('sale_ok', '=', True),
                    ('lifestyle_app_visible', '=', True),
                ], order='store_sequence asc, id desc', limit=section_limit)
            if process_section:
                process_items = homepage_section_items_by_section.get(process_section.id, request.env['ir.ui.view'].browse())
            if cta_section:
                cta_items = homepage_section_items_by_section.get(cta_section.id, request.env['ir.ui.view'].browse())

        featured_products = request.env['product.template'].sudo().search([
            ('sale_ok', '=', True),
            ('lifestyle_app_visible', '=', True),
        ], order='store_sequence asc, id desc', limit=featured_limit)

        return request.render('lifestyle_connector.lifestyle_homepage_direct_page', {
            'featured_products': featured_products,
            'homepage_slides': homepage_slides,
            'homepage_sections': homepage_sections,
            'homepage_top_sections': homepage_top_sections,
            'homepage_main_sections': homepage_main_sections,
            'homepage_bottom_sections': homepage_bottom_sections,
            'homepage_sections_ready': homepage_sections_ready,
            'homepage_section_items_by_section': homepage_section_items_by_section,
            'featured_products_by_section': featured_products_by_section,
            'featured_section': featured_section,
            'process_section': process_section,
            'process_items': process_items,
            'cta_section': cta_section,
            'cta_items': cta_items,
        })

    @http.route(['/contactus', '/contact-us'], type='http', auth='public', website=True, sitemap=True)
    def contactus(self, **kwargs):
        return request.render('lifestyle_connector.lifestyle_contactus_direct_page', {})

    @http.route('/contactus-thank-you', type='http', auth='public', website=True, sitemap=False)
    def contactus_thank_you(self, **kwargs):
        return request.render('lifestyle_connector.lifestyle_contactus_thank_you_page', {})

    @http.route(['/christianrevive', '/christianrevive/shop'], type='http', auth='public',
                website=True, sitemap=True)
    def christian_revive_store(self, search='', categ=None, **kwargs):
        """Christian Revive storefront: the web counterpart of the OneVoice27
        app's Store tab. Shows products flagged 'Show in Christian Revive
        App' (is_store_product); buying flows through the standard product
        page, cart and checkout shared with the Lifestyle shop."""
        Product = request.env['product.template'].sudo()
        domain = Product._cr_app_visibility_domain() + [
            ('sale_ok', '=', True), ('active', '=', True),
        ]
        search_text = str(search or '').strip()[:80]
        if search_text:
            domain.append(('name', 'ilike', search_text))
        all_products = Product.search(domain, order='store_sequence asc, id desc')
        categories = all_products.mapped('categ_id').sorted('name')
        categ_id = int(categ) if categ and str(categ).isdigit() else None
        products = (
            all_products.filtered(lambda p: p.categ_id.id == categ_id)
            if categ_id else all_products
        )
        deal_products = products.filtered(
            lambda p: p.compare_price and p.compare_price > p.list_price)
        return request.render('lifestyle_connector.christian_revive_storefront', {
            'products': products,
            'categories': categories,
            'active_categ_id': categ_id,
            'search_query': search_text,
            'deal_count': len(deal_products),
        })

class LifestyleCart(Cart):
    """Require a signed-in customer before anything enters the cart.

    Orders must belong to a real account so stage updates always have an
    email (or app push) channel and the customer can track progress in
    the portal. The storefront JS redirects guests to the login page
    before this ever fires; this server check is the safety net.
    """

    @http.route()
    def add_to_cart(self, *args, **kwargs):
        if request.env.user._is_public():
            raise UserError('Please sign in to add products to your cart.')
        product_id = kwargs.get('product_id') or kwargs.get('product_template_id')
        if not product_id and args:
            product_id = args[0]
        try:
            product = request.env['product.product'].sudo().browse(int(product_id or 0))
            product_tmpl = product.product_tmpl_id if product.exists() else request.env['product.template'].sudo().browse(int(product_id or 0))
            if product_tmpl.exists() and product_tmpl.is_storable and product_tmpl.rl_available_qty <= 0:
                raise UserError('This product is made to order. Please use the Made to order button.')
        except UserError:
            raise
        except Exception:
            pass
        return super().add_to_cart(*args, **kwargs)


class LifestyleWebsiteSale(WebsiteSale):
    """Website checkout customizations for Revive Lifestyle."""

    @http.route('/shop/rl_login_status', type='json', auth='public', website=True, methods=['POST'])
    def rl_login_status(self, **kw):
        """Lets the storefront JS know whether to send guests to login."""
        return {'logged_in': not request.env.user._is_public()}

    @http.route('/shop/rl_selected_color', type='json', auth='public', website=True, methods=['POST'])
    def rl_selected_color(self, product_id=None, **kw):
        """Color the visitor previously picked for this product (session),
        so the product page can pre-select the swatch after e.g. a login
        round-trip - the cart applies it either way, the UI should agree."""
        color = ''
        color_map = request.session.get('rl_product_colors') or {}
        if product_id and isinstance(color_map, dict):
            color = str(color_map.get(str(product_id)) or '')
        return {'color': color}

    @http.route('/shop/select_color', type='json', auth='public', website=True, methods=['POST'])
    def select_product_color(self, color='', product_id=None, **kw):
        """Store the customer's chosen color in session; cart update reads it."""
        color_text = str(color or '').strip()[:64]
        request.session['rl_product_color'] = color_text
        if product_id:
            color_map = dict(request.session.get('rl_product_colors') or {})
            color_map[str(product_id)] = color_text
            request.session['rl_product_colors'] = color_map
        return {'ok': True}

    @staticmethod
    def _lifestyle_cart_order():
        """Current website cart across Odoo versions.

        Odoo 19 dropped website.sale_get_order() in favour of the
        request.cart property; every color endpoint died on the old call.
        """
        order = getattr(request, 'cart', None)
        if order is None and hasattr(request.website, 'sale_get_order'):
            order = request.website.sale_get_order()
        return order

    def _lifestyle_apply_selected_color(self, product_id=None, line_id=None, color=''):
        color_text = str(color or '').strip()[:64]
        if not color_text:
            return {'ok': False}
        order = self._lifestyle_cart_order()
        if not order:
            return {'ok': False}
        line = request.env['sale.order.line'].sudo().browse()
        if line_id:
            line = order.order_line.filtered(lambda value: value.id == int(line_id))[:1]
        if not line and product_id:
            pid = int(product_id)
            lines = order.order_line.filtered(
                lambda value: value.product_id.id == pid or value.product_id.product_tmpl_id.id == pid
            ).sorted('id', reverse=True)
            line = lines[:1]
        if not line:
            return {'ok': False}
        line._lifestyle_apply_color(color_text)
        return {'ok': True, 'line_id': line.id, 'color': line.lifestyle_color}

    # NOTE: the pre-19 cart_update/cart_update_json route overrides were
    # removed: Odoo 19 registers its own POST /shop/cart/update (jsonrpc)
    # route, so redefining that path here shadowed core cart updates, and
    # the parent methods they super()'d into no longer exist. The color is
    # now stamped in sale.order._cart_add (models/sale_order.py).

    @http.route('/shop/notify_stock', type='json', auth='public', website=True, methods=['POST'])
    def notify_stock(self, product_id=None, email='', **kw):
        """Create a CRM lead so staff can follow up on made-to-order requests."""
        if not product_id:
            return {'ok': False}
        try:
            product = request.env['product.template'].sudo().browse(int(product_id))
            if not product.exists():
                return {'ok': False}
            partner = None
            email_from = str(email or '').strip()
            if not request.env.user._is_public():
                partner = request.env.user.partner_id
                email_from = partner.email or email_from
            lead_name = 'Made to Order: %s' % product.name
            duplicate_domain = [
                ('name', '=', lead_name),
                ('active', '=', True),
            ]
            if partner:
                duplicate_domain.append(('partner_id', '=', partner.id))
            elif email_from:
                duplicate_domain.append(('email_from', '=', email_from))
            else:
                requested_products = set(request.session.get('rl_mto_requested_products') or [])
                if int(product.id) in requested_products:
                    return {'ok': True, 'already': True}
            if partner or email_from:
                existing = request.env['crm.lead'].sudo().search(duplicate_domain, limit=1)
                if existing:
                    return {'ok': True, 'already': True}
            CrmTag = request.env['crm.tag'].sudo()
            tag = CrmTag.search([('name', '=', 'Made to Order')], limit=1)
            if not tag:
                tag = CrmTag.create({'name': 'Made to Order'})
            lead_vals = {
                'name': lead_name,
                'type': 'opportunity',
                'description': (
                    'Customer clicked Made to order on the website.\n\n'
                    'Product: %s\nProduct URL: %s%s'
                ) % (
                    product.name,
                    request.httprequest.host_url.rstrip('/'),
                    product.website_url or '',
                ),
                'tag_ids': [(4, tag.id)],
            }
            if email_from:
                lead_vals['email_from'] = email_from
            if partner:
                lead_vals['partner_id'] = partner.id
            request.env['crm.lead'].sudo().create(lead_vals)
            if not partner and not email_from:
                requested_products = set(request.session.get('rl_mto_requested_products') or [])
                requested_products.add(int(product.id))
                request.session['rl_mto_requested_products'] = list(requested_products)
            return {'ok': True}
        except Exception:
            return {'ok': False}

    @http.route('/shop/cart_line_colors', type='json', auth='public', website=True, methods=['POST'])
    def cart_line_colors(self, **kw):
        """Return selected colors for the current website cart."""
        order = self._lifestyle_cart_order()
        if not order:
            return {'lines': []}
        lines = []
        for line in order.order_line.filtered(lambda value: value.lifestyle_color):
            lines.append({
                'line_id': line.id,
                'product': line.product_id.display_name,
                'template': line.product_id.product_tmpl_id.display_name,
                'color': line.lifestyle_color,
                'quantity': line.product_uom_qty,
            })
        return {'lines': lines}

    @http.route('/shop/apply_color_to_cart', type='json', auth='public', website=True, methods=['POST'])
    def apply_color_to_cart(self, product_id=None, color='', **kw):
        """Click-listener fallback: apply color to the most recently added line for
        this product template in the current cart, called ~1.2 s after Add to Cart."""
        if not product_id or not color:
            return {'ok': False}
        try:
            order = self._lifestyle_cart_order()
            if not order:
                return {'ok': False}
            pid = int(product_id)
            lines = order.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id.id == pid
            ).sorted('id', reverse=True)
            if not lines:
                return {'ok': False}
            lines[0]._lifestyle_apply_color(str(color).strip())
            return {'ok': True, 'line_id': lines[0].id, 'color': lines[0].lifestyle_color}
        except Exception:
            return {'ok': False}

    @http.route('/shop/apply_line_color', type='json', auth='public', website=True, methods=['POST'])
    def apply_line_color(self, line_id=None, color='', **kw):
        """Apply the chosen color to a specific order line after Odoo's cart update.

        The JS fetch intercept calls this with the exact line_id returned by
        Odoo's own cart-update response, so we always find the right line.
        """
        if not line_id or not color:
            return {'ok': False}
        try:
            order = self._lifestyle_cart_order()
            if not order:
                return {'ok': False}
            lid = int(line_id)
            line = order.order_line.filtered(lambda l: l.id == lid)
            if line:
                line._lifestyle_apply_color(color)
                return {'ok': True, 'line_id': line.id, 'color': line.lifestyle_color}
            return {'ok': False}
        except Exception:
            return {'ok': False}

    def _get_shop_sortings(self, *args, **kwargs):
        sortings = super()._get_shop_sortings(*args, **kwargs)
        sortings.update({
            'newest': {'label': 'Newest pieces', 'order': 'create_date desc, id desc'},
            'price_asc': {'label': 'Price: low to high', 'order': 'list_price asc, id desc'},
            'price_desc': {'label': 'Price: high to low', 'order': 'list_price desc, id desc'},
            'name_asc': {'label': 'Name A-Z', 'order': 'name asc, id desc'},
        })
        return sortings
    def _validate_address_values(self, *args, **kwargs):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(*args, **kwargs)

        # Odoo blocks checkout name/email edits for internal users with a
        # backend-oriented message. Revive uses the website as the customer
        # checkout too, so allow these edits while keeping required-field,
        # invoice/VAT, and invalid email validations intact.
        filtered_messages = []
        removed_identity_message = False
        for message in error_messages:
            message_text = str(message)
            if (
                'external person' in message_text
                and 'backend' in message_text
                and 'account settings' in message_text
            ):
                removed_identity_message = True
                continue
            filtered_messages.append(message)

        if removed_identity_message:
            if not any('Invalid Email' in str(message) for message in filtered_messages):
                self._remove_invalid_checkout_field(invalid_fields, 'email')
            if not any('Changing your name is not allowed' in str(message) for message in filtered_messages):
                self._remove_invalid_checkout_field(invalid_fields, 'name')

        return invalid_fields, missing_fields, filtered_messages

    @staticmethod
    def _remove_invalid_checkout_field(invalid_fields, field_name):
        if hasattr(invalid_fields, 'discard'):
            invalid_fields.discard(field_name)
        elif field_name in invalid_fields:
            invalid_fields.remove(field_name)
