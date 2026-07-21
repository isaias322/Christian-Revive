# -*- coding: utf-8 -*-
{
    'name': 'Marketplace Core',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Peer-to-peer marketplace engine: sellers, KYC, listings, escrow, disputes, reviews',
    'description': """
Marketplace Core
================
The business-logic backbone of a Vinted-style peer-to-peer marketplace:

* Seller shops with onboarding, KYC and approval workflow
* Listings (condition, brand, size) with moderation and banned-item enforcement
* Escrow: funds held until buyer confirms delivery, then released to seller wallet
* Seller wallet + payout requests (bank / JazzCash / EasyPaisa)
* Buyer protection fee engine (fixed + percentage)
* Disputes with refund / release resolution
* Reviews and seller ratings
* Buyer-seller messaging threads
* Courier registry (TCS, Leopards, M&P, BlueEx, ...) with tracking links & COD support
""",
    'author': 'Marketplace Dev Team',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'portal',
        'sale_management',
        'website_sale',
    ],
    'data': [
        'security/marketplace_security.xml',
        'security/ir.model.access.csv',
        'data/marketplace_data.xml',
        'data/marketplace_cron.xml',
        'data/mail_templates.xml',
        'views/seller_views.xml',
        'views/listing_views.xml',
        'views/order_views.xml',
        'views/dispute_views.xml',
        'views/review_views.xml',
        'views/messaging_views.xml',
        'views/payout_views.xml',
        'views/courier_views.xml',
        'views/config_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
}
