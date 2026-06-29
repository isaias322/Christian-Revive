# -*- coding: utf-8 -*-
def migrate(cr, version):
    """One-time backfill: products that already had "Show in Revive
    Lifestyle App" checked before website_published syncing existed never
    got their website_published field updated, so they kept showing the
    "Unpublished" ribbon on the storefront even though they're correctly
    app-visible. Re-running the sync now catches all of them."""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    products = env['product.template'].search([])
    products._lifestyle_sync_website_published()
