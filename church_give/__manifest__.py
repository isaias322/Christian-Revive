# -*- coding: utf-8 -*-
{
    'name': 'Church Give — Donations & Tithes',
    'version': '19.0.1.0.0',
    'category': 'Church Management',
    'summary': 'Manage tithes, offerings, and donations from the Christian Revive app',
    'description': """
        Church Give Module
        ==================
        - Receive donations from the Flutter mobile app
        - Support EasyPaisa, JazzCash, Stripe, PayPal, Cash
        - Full transaction history per member/partner/volunteer
        - Receipt generation
        - Dashboard with totals by category and gateway
        - REST-style JSON-RPC API for Flutter integration
    """,
    'author': 'Christian Revive',
    'website': 'https://christianrevive.com',
    'depends': ['base', 'mail'],
    'data': [
        'security/church_give_security.xml',
        'security/ir.model.access.csv',
        'views/church_give_transaction.xml',
        'views/church_give_menu.xml',
        'data/church_give_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}