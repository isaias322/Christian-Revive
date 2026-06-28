# -*- coding: utf-8 -*-
from odoo import api, models, fields


class ProductTemplate(models.Model):
    """revive_db is shared with the Revive App backend, so the product
    catalog needs an explicit boundary between the two apps' inventories -
    without this, the Lifestyle app would show every sellable product on
    the whole shared database, including the other app's items."""
    _inherit = 'product.template'

    review_ids = fields.One2many('lifestyle.product.review', 'product_tmpl_id', string='Reviews')
    color_image_ids = fields.One2many(
        'lifestyle.product.color.image',
        'product_tmpl_id',
        string='App Color Images',
        help='Unlimited color/finish images used by the Revive Lifestyle app.',
    )

    # store_rating/store_review_count were plain manually-typed fields on
    # volunteer_and_donation_management's product.template extension; this
    # module depends on that one and loads after it, so redeclaring them
    # here as computed converts them to automatic (no more hand-entry) for
    # both apps without touching the other addon's code.
    store_rating = fields.Float(string='Rating', compute='_compute_store_rating', compute_sudo=True, store=True)
    store_review_count = fields.Integer(string='Review Count', compute='_compute_store_rating', compute_sudo=True, store=True)
    store_sold_count = fields.Integer(string='Sold Count', compute='_compute_store_sold_count')

    @api.depends('review_ids.rating')
    def _compute_store_rating(self):
        for product in self:
            reviews = product.sudo().review_ids
            product.store_review_count = len(reviews)
            product.store_rating = (sum(reviews.mapped('rating')) / len(reviews)) if reviews else 0.0

    def _compute_store_sold_count(self):
        SaleLine = self.env['sale.order.line'].sudo()
        for product in self:
            variant_ids = product.product_variant_ids.ids
            if not variant_ids:
                product.store_sold_count = 0
                continue
            lines = SaleLine.search([
                ('product_id', 'in', variant_ids),
                ('order_id.state', 'in', ('sale', 'done')),
            ])
            product.store_sold_count = int(sum(lines.mapped('product_uom_qty')))

    def _get_lifestyle_color_selection(self):
        colors = set()
        products = self.env['product.template'].search([('color_options', '!=', False)])
        for product in products:
            for value in (product.color_options or '').split(','):
                color = value.strip()
                if color:
                    colors.add(color)
        return [(color, color) for color in sorted(colors, key=str.lower)]

    lifestyle_app_visible = fields.Boolean(
        string='Show in Revive Lifestyle App',
        default=False,
        help='Only products with this checked appear in the Revive Lifestyle mobile app catalog.',
    )
    # Image (not Binary) so Odoo auto-resizes/compresses on upload instead of
    # storing whatever full-camera-resolution file the admin picked — that
    # was why switching colors in the app took forever to load.
    lifestyle_color_image_1_color = fields.Selection(selection='_get_lifestyle_color_selection', string='Color for Image 1')
    lifestyle_color_image_1 = fields.Image(string='Color Image 1', max_width=1024, max_height=1024)
    lifestyle_color_image_2_color = fields.Selection(selection='_get_lifestyle_color_selection', string='Color for Image 2')
    lifestyle_color_image_2 = fields.Image(string='Color Image 2', max_width=1024, max_height=1024)
    lifestyle_color_image_3_color = fields.Selection(selection='_get_lifestyle_color_selection', string='Color for Image 3')
    lifestyle_color_image_3 = fields.Image(string='Color Image 3', max_width=1024, max_height=1024)
    lifestyle_color_image_4_color = fields.Selection(selection='_get_lifestyle_color_selection', string='Color for Image 4')
    lifestyle_color_image_4 = fields.Image(string='Color Image 4', max_width=1024, max_height=1024)

    # store_image_2/3/4 are plain Binary fields on volunteer_and_donation_management;
    # redeclared here as Image for the same reason, same override pattern as store_rating above.
    store_image_2 = fields.Image(string='Store Image 2', max_width=1024, max_height=1024)
    store_image_3 = fields.Image(string='Store Image 3', max_width=1024, max_height=1024)
    store_image_4 = fields.Image(string='Store Image 4', max_width=1024, max_height=1024)

    # Optional cross-sell link: when set, tapping that "More views" thumbnail
    # in the app opens the linked product instead of just zooming the photo.
    store_image_2_product_id = fields.Many2one(
        'product.template', string='Image 2 Links To Product',
        help='Optional. If set, tapping this photo in the app opens that product page instead of zooming in.',
    )
    store_image_3_product_id = fields.Many2one(
        'product.template', string='Image 3 Links To Product',
        help='Optional. If set, tapping this photo in the app opens that product page instead of zooming in.',
    )
    store_image_4_product_id = fields.Many2one(
        'product.template', string='Image 4 Links To Product',
        help='Optional. If set, tapping this photo in the app opens that product page instead of zooming in.',
    )

    def action_optimize_lifestyle_images(self):
        """Re-saves every image field on these products through itself,
        which makes Odoo re-run the Image field's resize/compression step —
        shrinks any oversized photo that was uploaded before these fields
        were switched from Binary to Image."""
        image_fields = (
            'lifestyle_color_image_1', 'lifestyle_color_image_2',
            'lifestyle_color_image_3', 'lifestyle_color_image_4',
            'store_image_2', 'store_image_3', 'store_image_4',
        )
        for product in self:
            for field_name in image_fields:
                if field_name in product._fields and getattr(product, field_name):
                    product.write({field_name: getattr(product, field_name)})
            for color_image in product.color_image_ids:
                if color_image.image:
                    color_image.write({'image': color_image.image})



