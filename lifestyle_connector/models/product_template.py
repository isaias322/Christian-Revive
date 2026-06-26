# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    """revive_db is shared with the Revive App backend, so the product
    catalog needs an explicit boundary between the two apps' inventories â€”
    without this, the Lifestyle app would show every sellable product on
    the whole shared database, including the other app's items."""
    _inherit = 'product.template'

    lifestyle_app_visible = fields.Boolean(
        string='Show in Revive Lifestyle App',
        default=False,
        help='Only products with this checked appear in the Revive Lifestyle mobile app catalog.',
    )
    lifestyle_color_image_1 = fields.Binary(string='Color Image 1')
    lifestyle_color_image_2 = fields.Binary(string='Color Image 2')
    lifestyle_color_image_3 = fields.Binary(string='Color Image 3')
    lifestyle_color_image_4 = fields.Binary(string='Color Image 4')

