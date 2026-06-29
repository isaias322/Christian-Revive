# -*- coding: utf-8 -*-
{
    'name': 'Revive Lifestyle Connector',
    'version': '1.0.2',
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
    'depends': [
        'base', 'mail', 'account', 'sale_management', 'stock', 'crm', 'delivery', 'portal', 'hr',
        'website', 'website_sale', 'website_crm',
        'volunteer_and_donation_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/product_category_data.xml',
        'views/sale_order_views.xml',
        'views/product_template_views.xml',
        'views/app_banner_views.xml',
        'views/product_review_views.xml',
        'views/hr_employee_views.xml',
        'views/website_templates.xml',
        'views/vendor_portal_templates.xml',
        'data/website_branding_data.xml',
        'data/website_categories_data.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'lifestyle_connector/static/src/scss/lifestyle_web_theme_vars.scss',
        ],
        'web.assets_frontend': [
            'lifestyle_connector/static/src/scss/lifestyle_web_theme.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}

