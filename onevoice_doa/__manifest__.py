# -*- coding: utf-8 -*-
{
    'name': 'Study Books',
    'version': '1.2.3',
    'category': 'Church Management',
    'summary': 'Manages study books (Desire of Ages, Daniel, Revelation, etc.) for the OneVoice app',
    'author': 'Christian Revive',
    'website': 'https://christianrevive.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/study_book_views.xml',
        'views/doa_chapter_views.xml',
        'views/study_mcq_views.xml',
        'views/doa_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
