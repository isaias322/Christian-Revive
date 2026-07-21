# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    marketplace_seller_ids = fields.One2many(
        'marketplace.seller', 'partner_id', string='Marketplace Shops')
    marketplace_favorite_ids = fields.Many2many(
        'product.template', 'marketplace_listing_favorite_rel',
        'partner_id', 'product_tmpl_id', string='Favourite Listings')
    marketplace_followed_shop_ids = fields.Many2many(
        'marketplace.seller', 'marketplace_seller_follower_rel',
        'partner_id', 'seller_id', string='Followed Shops')

    def get_marketplace_seller(self):
        """Return this partner's shop (or empty recordset)."""
        self.ensure_one()
        return self.marketplace_seller_ids[:1]
