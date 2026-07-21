# -*- coding: utf-8 -*-
import logging

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
STRIPE_API_BASE = 'https://api.stripe.com/v1'


class MarketplaceCartItem(models.Model):
    """Server-side cart shared by the website and the mobile app.

    Marketplace items are unique (quantity 1), so the cart is simply the
    set of listings a buyer intends to purchase. At checkout the cart is
    split into one order per seller.
    """
    _name = 'marketplace.cart.item'
    _description = 'Marketplace Cart Item'
    _order = 'create_date desc'

    partner_id = fields.Many2one(
        'res.partner', required=True, index=True, ondelete='cascade')
    product_tmpl_id = fields.Many2one(
        'product.template', string='Listing', required=True,
        ondelete='cascade')
    seller_id = fields.Many2one(
        related='product_tmpl_id.marketplace_seller_id', store=True)
    price = fields.Float(related='product_tmpl_id.list_price')

    _sql_constraints = [
        ('partner_product_uniq', 'unique(partner_id, product_tmpl_id)',
         'This item is already in your cart.'),
    ]

    @api.model
    def add_item(self, partner, product_tmpl):
        if product_tmpl.listing_state != 'active':
            raise UserError(_('This item is no longer available.'))
        if product_tmpl.marketplace_seller_id.partner_id == partner:
            raise UserError(_('You cannot buy your own listing.'))
        existing = self.sudo().search([
            ('partner_id', '=', partner.id),
            ('product_tmpl_id', '=', product_tmpl.id)], limit=1)
        return existing or self.sudo().create({
            'partner_id': partner.id,
            'product_tmpl_id': product_tmpl.id,
        })

    @api.model
    def get_cart(self, partner):
        items = self.sudo().search([('partner_id', '=', partner.id)])
        # Drop items sold in the meantime
        stale = items.filtered(
            lambda i: i.product_tmpl_id.listing_state != 'active')
        stale.unlink()
        return items - stale

    @api.model
    def checkout(self, partner, values, item_ids=None):
        """Create one confirmed marketplace order per seller from the cart.

        :param values: dict with shipping/contact info:
            name, phone, street, city, zip (optional), payment_method,
            courier_id (optional)
        :param item_ids: if given, checkout exactly these cart item ids
            instead of the buyer's current cart — used by the Stripe
            webhook to fulfil precisely what was paid for, in case the
            cart changed between session creation and payment completion.
        :returns: sale.order recordset (one per seller)
        """
        if item_ids is not None:
            items = self.sudo().browse(item_ids).exists().filtered(
                lambda i: i.partner_id == partner
                and i.product_tmpl_id.listing_state == 'active')
        else:
            items = self.get_cart(partner)
        if not items:
            raise UserError(_('Your cart is empty.'))
        required = ['name', 'phone', 'street', 'city', 'payment_method']
        missing = [f for f in required if not values.get(f)]
        if missing:
            raise UserError(_(
                'Missing checkout information: %s') % ', '.join(missing))

        partner_sudo = partner.sudo()
        partner_sudo.write({
            'phone': values['phone'],
            'street': values['street'],
            'city': values['city'],
            'zip': values.get('zip') or partner_sudo.zip,
        })
        if not partner_sudo.name:
            partner_sudo.write({'name': values['name']})

        Order = self.env['sale.order'].sudo()
        orders = Order.browse()
        courier = False
        if values.get('courier_id'):
            courier = self.env['marketplace.courier'].sudo().browse(
                int(values['courier_id']))
            courier = courier.exists() and courier or False

        sellers = items.mapped('seller_id')
        for seller in sellers:
            seller_items = items.filtered(lambda i: i.seller_id == seller)
            order = Order.create({
                'partner_id': partner.id,
                'currency_id': self.env.company.currency_id.id,
                'is_marketplace_order': True,
                'marketplace_seller_id': seller.id,
                'marketplace_payment_method': values['payment_method'],
                'marketplace_courier_id': courier and courier.id,
                'order_line': [(0, 0, {
                    'product_id': item.product_tmpl_id.product_variant_id.id,
                    'product_uom_qty': 1,
                    'price_unit': item.product_tmpl_id.list_price,
                }) for item in seller_items],
            })
            order._add_marketplace_fees(courier)
            order.action_confirm_marketplace()
            orders |= order

        items.sudo().unlink()
        return orders

    # ------------------------------------------------------------------
    # Card payments (Stripe Checkout)
    # ------------------------------------------------------------------
    @api.model
    def stripe_configured(self):
        return bool(self.env['ir.config_parameter'].sudo().get_param(
            'marketplace_core.stripe_secret_key'))

    @api.model
    def _compute_checkout_total(self, items, courier=None):
        """Mirrors the per-seller fee math in _add_marketplace_fees()
        without creating any orders — used to quote the Stripe charge
        before anything is booked."""
        icp = self.env['ir.config_parameter'].sudo()
        fixed = float(icp.get_param(
            'marketplace_core.buyer_protection_fixed', '100.0'))
        pct = float(icp.get_param(
            'marketplace_core.buyer_protection_pct', '5.0'))
        total = 0.0
        for seller in items.mapped('seller_id'):
            seller_items = items.filtered(lambda i: i.seller_id == seller)
            subtotal = sum(seller_items.mapped('price'))
            fee = fixed + subtotal * pct / 100.0
            ship = courier.flat_rate if courier and courier.flat_rate else 0.0
            total += subtotal + fee + ship
        return total

    @api.model
    def create_stripe_session(self, partner, values, success_url, cancel_url):
        """Opens a Stripe-hosted Checkout Session for the buyer's current
        cart. Nothing is booked yet — checkout() only runs once Stripe
        confirms payment via the /payment/stripe/webhook route, so a
        buyer who abandons the Stripe page simply leaves their cart
        untouched instead of leaving a half-paid order behind.
        """
        if not self.stripe_configured():
            raise UserError(_(
                'Card payments are not set up yet. Please choose another '
                'payment method.'))
        items = self.get_cart(partner)
        if not items:
            raise UserError(_('Your cart is empty.'))
        required = ['name', 'phone', 'street', 'city']
        missing = [f for f in required if not values.get(f)]
        if missing:
            raise UserError(_(
                'Missing checkout information: %s') % ', '.join(missing))

        courier = False
        if values.get('courier_id'):
            courier = self.env['marketplace.courier'].sudo().browse(
                int(values['courier_id']))
            courier = courier.exists() and courier or False

        amount = self._compute_checkout_total(items, courier)
        if amount <= 0:
            raise UserError(_('Nothing to charge.'))
        currency = self.env.company.currency_id.name.lower()
        secret_key = self.env['ir.config_parameter'].sudo().get_param(
            'marketplace_core.stripe_secret_key')

        metadata = {
            'partner_id': str(partner.id),
            'cart_item_ids': ','.join(str(i) for i in items.ids),
            'name': values['name'],
            'phone': values['phone'],
            'street': values['street'],
            'city': values['city'],
            'zip': values.get('zip') or '',
            'courier_id': str(courier.id) if courier else '',
        }
        payload = {
            'mode': 'payment',
            'success_url': success_url + '?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': cancel_url,
            'customer_email': partner.email or '',
            'line_items[0][price_data][currency]': currency,
            'line_items[0][price_data][product_data][name]':
                _('Marketplace order (%s item(s))') % len(items),
            'line_items[0][price_data][unit_amount]':
                str(int(round(amount * 100))),
            'line_items[0][quantity]': '1',
        }
        for key, value in metadata.items():
            payload['metadata[%s]' % key] = value

        try:
            resp = requests.post(
                '%s/checkout/sessions' % STRIPE_API_BASE, data=payload,
                auth=(secret_key, ''), timeout=15)
        except requests.RequestException as e:
            _logger.exception('Stripe session creation failed')
            raise UserError(_('Could not reach Stripe: %s') % str(e))
        if resp.status_code >= 400:
            _logger.error('Stripe error creating session: %s', resp.text)
            try:
                message = resp.json().get('error', {}).get('message')
            except ValueError:
                message = resp.text
            raise UserError(_('Stripe error: %s') % (message or resp.text))
        session = resp.json()
        return session['url']
