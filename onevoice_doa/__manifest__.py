# -*- coding: utf-8 -*-
{
    'name': 'Desire of Ages Chapters',
    'version': '1.0.0',
    'category': 'Church Management',
    'summary': 'Stores all Desire of Ages chapters (English & Urdu) for the OneVoice app',
    'author': 'Christian Revive',
    'website': 'https://christianrevive.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/doa_chapter_views.xml',
        'views/doa_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
