# -*- coding: utf-8 -*-
{
    'name': 'Revive Homepage Slider',
    'version': '1.0.0',
    'category': 'Website',
    'summary': 'Reusable website hero slider managed from Odoo',
    'description': """
        Revive Homepage Slider
        ======================
        Reusable website hero slides with editable images, text, buttons,
        feature chips, right-card content, background styles, and editable homepage sections.
    """,
    'author': 'Revive Lifestyle',
    'depends': ['base', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/homepage_slide_views.xml',
        'views/homepage_section_views.xml',
        'data/homepage_slide_data.xml',
        'data/homepage_section_data.xml',
        'data/homepage_slide_copy_fix_data.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
