# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


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

class LifestyleWebsiteSale(WebsiteSale):
    """Website checkout customizations for Revive Lifestyle."""

    @http.route('/shop/select_color', type='json', auth='public', website=True, methods=['POST'])
    def select_product_color(self, color='', **kw):
        """Store the customer's chosen color in session; SaleOrder._cart_update reads it."""
        request.session['rl_product_color'] = str(color).strip()[:64]
        return {'ok': True}

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
