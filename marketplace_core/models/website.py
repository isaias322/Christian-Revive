# -*- coding: utf-8 -*-
from odoo import models


class Website(models.Model):
    _inherit = 'website'

    def _product_domain(self):
        """Marketplace listings are sold through /market, not the default
        Odoo eCommerce /shop — keep the two catalogs separate."""
        domain = super()._product_domain()
        return domain + [('is_marketplace_listing', '=', False)]
