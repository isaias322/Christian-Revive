# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    marketplace_buyer_protection_fixed = fields.Float(
        string='Buyer Protection Fixed Fee',
        config_parameter='marketplace_core.buyer_protection_fixed',
        default=100.0,
        help='Fixed part of the buyer protection fee added at checkout '
             '(e.g. Rs 100 / £0.70).')
    marketplace_buyer_protection_pct = fields.Float(
        string='Buyer Protection Fee (%)',
        config_parameter='marketplace_core.buyer_protection_pct',
        default=5.0,
        help='Variable part of the buyer protection fee, % of item price.')
    marketplace_escrow_auto_release_days = fields.Integer(
        string='Escrow Auto-Release (days)',
        config_parameter='marketplace_core.escrow_auto_release_days',
        default=3,
        help='Days after delivery before held funds are automatically '
             'released to the seller if the buyer does not confirm or dispute.')
    marketplace_moderate_listings = fields.Boolean(
        string='Moderate Listings Before Publishing',
        config_parameter='marketplace_core.moderate_listings',
        help='If enabled, every new listing goes through manual moderation '
             'before appearing on the marketplace. If disabled, listings '
             'that pass the banned-item check go live immediately.')

    marketplace_stripe_publishable_key = fields.Char(
        string='Stripe Publishable Key',
        config_parameter='marketplace_core.stripe_publishable_key',
        help='From your Stripe Dashboard → Developers → API keys. '
             'Use a pk_test_... key while testing, pk_live_... once live.')
    marketplace_stripe_secret_key = fields.Char(
        string='Stripe Secret Key',
        config_parameter='marketplace_core.stripe_secret_key',
        groups='marketplace_core.group_marketplace_manager',
        help='From your Stripe Dashboard → Developers → API keys. '
             'Use a sk_test_... key while testing, sk_live_... once live. '
             'Card checkout is disabled until this is set.')
    marketplace_stripe_webhook_secret = fields.Char(
        string='Stripe Webhook Signing Secret',
        config_parameter='marketplace_core.stripe_webhook_secret',
        groups='marketplace_core.group_marketplace_manager',
        help='From the webhook endpoint you create in the Stripe Dashboard '
             'pointing at <your domain>/payment/stripe/webhook, listening '
             'for the checkout.session.completed event. Without this, '
             'incoming webhook calls are rejected.')

    marketplace_mto_deposit_pct = fields.Float(
        string='Made-to-Order Deposit (%)',
        config_parameter='marketplace_core.mto_deposit_pct',
        default=50.0,
        help='Percentage of the item price a buyer pays up front to start '
             'a made-to-order item; the rest is billed once the seller '
             'marks it ready to ship.')
    marketplace_fcm_project_id = fields.Char(
        string='Firebase Project ID',
        config_parameter='marketplace_core.fcm_project_id',
        groups='marketplace_core.group_marketplace_manager',
        help='Firebase project ID (Project Settings → General). '
             'Push notifications are disabled until this and the service '
             'account key below are both set.')
    marketplace_fcm_service_account_json = fields.Text(
        string='Firebase Service Account JSON',
        config_parameter='marketplace_core.fcm_service_account_json',
        groups='marketplace_core.group_marketplace_manager',
        help='The full JSON key file from Firebase → Project Settings → '
             'Service Accounts → Generate new private key. Paste the '
             "entire file contents here. Never shipped to the app - "
             'server-side only.')
