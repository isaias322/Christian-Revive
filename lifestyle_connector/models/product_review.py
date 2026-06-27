# -*- coding: utf-8 -*-
from odoo import fields, models


class LifestyleProductReview(models.Model):
    """A customer's star rating + comment on a product, submitted from the
    Revive Lifestyle app. product.template's store_rating/store_review_count
    are computed from these (see product_template.py) instead of being typed
    in by hand."""
    _name = 'lifestyle.product.review'
    _description = 'Revive Lifestyle Product Review'
    _order = 'create_date desc'

    product_tmpl_id = fields.Many2one('product.template', string='Product', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    rating = fields.Integer(string='Rating', required=True)
    comment = fields.Text(string='Comment')

    _sql_constraints = [
        ('rating_range', 'CHECK(rating >= 1 AND rating <= 5)', 'Rating must be between 1 and 5.'),
        ('one_review_per_customer', 'unique(product_tmpl_id, partner_id)', 'You have already reviewed this product.'),
    ]
