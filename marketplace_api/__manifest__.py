# -*- coding: utf-8 -*-
{
    'name': 'Marketplace REST API',
    'version': '19.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Token-based JSON REST API for the marketplace mobile app (Flutter)',
    'description': """
Marketplace REST API
====================
Versioned JSON API consumed by the Flutter mobile app:

* /api/v1/auth       - register, login, logout, profile
* /api/v1/listings   - search, detail, create, update, delete
* /api/v1/shops      - shop pages, follow, seller dashboard
* /api/v1/cart       - server-side cart + checkout
* /api/v1/orders     - buyer & seller order flows, escrow actions
* /api/v1/threads    - buyer-seller messaging
* /api/v1/reviews    - ratings & reviews
* /api/v1/disputes   - dispute creation

Authentication: Bearer token in the Authorization header.
""",
    'author': 'Marketplace Dev Team',
    'license': 'LGPL-3',
    'depends': [
        'marketplace_core',
        'auth_signup',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/api_cron.xml',
    ],
    'installable': True,
    'application': False,
}
