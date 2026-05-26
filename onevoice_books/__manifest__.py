# -*- coding: utf-8 -*-
{
    'name': 'OneVoice Books',
    'version': '1.0.0',
    'category': 'Church Management',
    'summary': 'Multi-book chapter reader for the OneVoice app (Desire of Ages, Patriarchs & Prophets, etc.)',
    'author': 'Christian Revive',
    'website': 'https://christianrevive.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/onevoice_book_views.xml',
        'views/onevoice_books_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
