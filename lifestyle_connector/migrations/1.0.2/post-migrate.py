# -*- coding: utf-8 -*-
def migrate(cr, version):
    """One-time backfill: tag existing products into the new website public
    categories (Furniture & Home / Fruits & Vegetables / Healthy Pantry) so
    the Shop menu's category dropdown has something to show immediately,
    without waiting for each product to be re-saved."""
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    products = env['product.template'].search([])
    products._lifestyle_sync_public_category()
