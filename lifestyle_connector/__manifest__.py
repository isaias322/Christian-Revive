# -*- coding: utf-8 -*-
{
    'name': 'Revive Lifestyle Connector',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Mobile app glue: order fulfillment timeline, FCM push notifications, REST API for the Revive Lifestyle Flutter app',
    'description': """
        Revive Lifestyle Connector
        ==========================
        Thin integration layer on top of standard Odoo apps (Sales, Inventory, CRM)
        for the Revive Lifestyle e-commerce mobile app:
        - Fulfillment type (Delivery / Pickup) and a customer-facing delivery stage timeline on Sales Orders
        - Firebase Cloud Messaging push notifications to customers (status updates + vendor photo sharing)
        - Public/portal REST API consumed by the Flutter app (catalog, checkout, orders, device registration)
    """,
    'author': 'Revive Lifestyle',
    'depends': ['base', 'mail', 'sale_management', 'stock', 'crm', 'delivery', 'portal', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/product_category_data.xml',
        'views/sale_order_views.xml',
        'views/product_template_views.xml',
        'views/app_banner_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}

