# -*- coding: utf-8 -*-
from odoo import models


class Website(models.Model):
    """Keeps the public shop restricted to the same products the Revive
    Lifestyle app shows. Odoo's own product_domain only filters by
    published-state for non-staff visitors, so an internal/admin preview
    (and any other product in this shared database) would otherwise leak
    through onto this storefront."""
    _inherit = 'website'

    def _product_domain(self):
        domain = super()._product_domain()
        return domain + self.env['product.template']._lifestyle_app_visibility_domain()
