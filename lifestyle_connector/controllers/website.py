# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class LifestyleWebsite(http.Controller):

    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def homepage(self, **kwargs):
        featured_products = request.env['product.template'].sudo().search([
            ('sale_ok', '=', True),
            ('lifestyle_app_visible', '=', True),
        ], order='store_sequence asc, id desc', limit=4)
        homepage_slides = request.env['ir.ui.view'].browse()
        if request.env.registry.get('lifestyle.homepage.slide'):
            homepage_slides = request.env['lifestyle.homepage.slide'].sudo().search([
                ('active', '=', True),
            ], order='sequence, id')
        return request.render('lifestyle_connector.lifestyle_homepage_direct_page', {
            'featured_products': featured_products,
            'homepage_slides': homepage_slides,
        })

    @http.route(['/contactus', '/contact-us'], type='http', auth='public', website=True, sitemap=True)
    def contactus(self, **kwargs):
        return request.render('lifestyle_connector.lifestyle_contactus_direct_page', {})

    @http.route('/contactus-thank-you', type='http', auth='public', website=True, sitemap=False)
    def contactus_thank_you(self, **kwargs):
        return request.render('lifestyle_connector.lifestyle_contactus_thank_you_page', {})

class LifestyleWebsiteSale(WebsiteSale):
    """Website checkout customizations for Revive Lifestyle."""

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
