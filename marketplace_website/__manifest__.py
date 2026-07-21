# -*- coding: utf-8 -*-
{
    'name': 'Marketplace Website',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Storefront for the peer-to-peer marketplace: browse, sell, chat, checkout',
    'description': """
Marketplace Website
===================
Buyer and seller front-end on the Odoo website:

* Marketplace home with feed, categories and featured shops
* Search with filters (category, brand, size, condition, price)
* Item pages with photo gallery, favourites and seller card
* Public shop pages with follow button and reviews
* Sell flow: create a shop, list items with multi-photo upload
* Seller dashboard: stats, listings, orders, wallet, payouts, KYC
* Cart & checkout with buyer protection fee and COD/JazzCash/EasyPaisa/bank
* Buyer orders: tracking, confirm delivery, disputes, reviews
* Buyer-seller messaging with a chat UI
""",
    'author': 'Marketplace Dev Team',
    'license': 'LGPL-3',
    'depends': [
        'marketplace_core',
        'website',
        'auth_signup',
    ],
    'data': [
        'data/website_data.xml',
        'views/templates_layout.xml',
        'views/templates_market.xml',
        'views/templates_item.xml',
        'views/templates_shop.xml',
        'views/templates_sell.xml',
        'views/templates_dashboard.xml',
        'views/templates_cart.xml',
        'views/templates_account.xml',
        'views/templates_messages.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'marketplace_website/static/src/css/marketplace.css',
            'marketplace_website/static/src/js/marketplace.js',
        ],
    },
    'installable': True,
    'application': False,
}
