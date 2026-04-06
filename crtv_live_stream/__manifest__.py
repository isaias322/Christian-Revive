{
    'name': 'CRTV Live Stream',
    'version': '19.0.1.0.0',
    'summary': 'Manage live streams, TV schedules and program listings',
    'author': 'CRTV',
    'category': 'Broadcasting',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/live_stream_views.xml',
        'views/live_stream_menus.xml',
        'views/live_stream_cron.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}