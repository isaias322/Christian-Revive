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
    rl_available_qty = fields.Integer(
        string='Available to Promise',
        compute='_compute_rl_available_qty',
        help='On-hand stock minus undelivered confirmed order quantities.',
    )
    lifestyle_room = fields.Selection([
        ('bedroom', 'Bedroom'),
        ('living_room', 'Living Room'),
        ('dining_room', 'Dining Room'),
        ('office', 'Office'),
        ('outdoor', 'Outdoor'),
        ('kids_room', 'Kids Room'),
        ('entryway', 'Entryway'),
        ('custom', 'Custom / Other'),
    ], string='Room (legacy)', help='Replaced by lifestyle_room_ids. Kept to avoid data loss.')
    lifestyle_room_ids = fields.Many2many(
        'lifestyle.room.category',
        'lifestyle_product_room_rel',
        'product_id',
        'room_id',
        string='Rooms for Website Shop',
        help='Which rooms this product appears in on the website Shop by Room filter.',
    )

    @api.depends('review_ids.rating', 'review_ids.write_date')
    def _compute_store_rating(self):
        for product in self:
            reviews = product.sudo().review_ids.sorted(
                key=lambda review: (review.write_date or review.create_date, review.id),
                reverse=True,
            )
            latest_by_partner = {}
            for review in reviews:
                latest_by_partner.setdefault(review.partner_id.id, review)
            unique_reviews = list(latest_by_partner.values())
            product.store_review_count = len(unique_reviews)
            product.store_rating = (
                sum(review.rating for review in unique_reviews) / len(unique_reviews)
            ) if unique_reviews else 0.0

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

    def _compute_rl_available_qty(self):
        """On-hand stock minus quantities already committed to customers.

        The public shop should reflect the Revive order flow, not only stock
        moves. A website order can exist before delivery is validated, so we
        subtract non-cancelled order lines until the order reaches the final
        delivered/picked-up stage or the line itself is fully delivered.
        """
        SaleLine = self.env['sale.order.line'].sudo()
        final_stages = ('delivered', 'picked_up', 'cancelled')
        for product in self:
            # Odoo 19 dropped type='product'; storable goods are
            # type='consu' with is_storable=True. The old type check made
            # this compute return 0 for every product.
            if not product.is_storable:
                product.rl_available_qty = 0
                continue
            variant_ids = product.product_variant_ids.ids
            if not variant_ids:
                product.rl_available_qty = max(0, int(product.qty_available))
                continue
            lines = SaleLine.search([
                ('product_id', 'in', variant_ids),
                ('order_id.state', '!=', 'cancel'),
                ('order_id.delivery_stage', 'not in', final_stages),
            ])
            committed = sum(max(0.0, line.product_uom_qty - line.qty_delivered) for line in lines)
            product.rl_available_qty = max(0, int(product.qty_available - committed))

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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._lifestyle_sync_website_published()
        records._lifestyle_sync_public_category()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'is_store_product' in vals or 'lifestyle_app_visible' in vals:
            self._lifestyle_sync_website_published()
        if 'categ_id' in vals:
            self._lifestyle_sync_public_category()
        return res

    def _lifestyle_sync_public_category(self):
        """Tags each product into the website's public category matching
        its internal Revive Lifestyle category, so the Shop menu's category
        dropdown filters correctly without admins managing two separate
        category trees by hand."""
        if 'public_categ_ids' not in self._fields:
            return
        mapping = [
            ('lifestyle_connector.category_furniture_home', 'lifestyle_connector.public_category_furniture'),
            ('lifestyle_connector.category_fruits_veg', 'lifestyle_connector.public_category_fruits_veg'),
            ('lifestyle_connector.category_healthy_pantry', 'lifestyle_connector.public_category_pantry'),
        ]
        for internal_xml_id, public_xml_id in mapping:
            internal_categ = self.env.ref(internal_xml_id, raise_if_not_found=False)
            public_categ = self.env.ref(public_xml_id, raise_if_not_found=False)
            if not internal_categ or not public_categ:
                continue
            matching = self.filtered(lambda p: p.categ_id.id == internal_categ.id or p.categ_id.parent_path and str(internal_categ.id) in p.categ_id.parent_path.split('/'))
            if matching:
                matching.write({'public_categ_ids': [(4, public_categ.id)]})

    def _lifestyle_is_app_visible(self):
        self.ensure_one()
        return bool(self.lifestyle_app_visible)

    @api.model
    def _lifestyle_app_visibility_domain(self):
        """Single source of truth for "is this product part of the Revive
        Lifestyle catalog" - shared by the app's API and the website's shop
        domain so the two surfaces can never drift apart.

        Deliberately independent from is_store_product: that flag is the
        Christian Revive app/website catalog, and each brand is curated by
        its own checkbox on the product form."""
        return [('lifestyle_app_visible', '=', True)]

    def _lifestyle_sync_website_published(self):
        """Keeps the public website in lockstep with the app catalog flags.

        A product page must be publicly reachable when EITHER brand lists
        the product: the Lifestyle shop and the Christian Revive storefront
        both link to the same website product page."""
        if 'website_published' not in self._fields:
            return
        for product in self:
            visible = bool(product.lifestyle_app_visible or product.is_store_product)
            if product.website_published != visible:
                product.website_published = visible

    @api.model
    def _lifestyle_available_colors(self):
        """Distinct colors across the visible catalog, for the website's
        color filter - color_options is a plain comma-separated Char field,
        not a real Odoo attribute, so this can't use the native filters."""
        products = self.sudo().search(
            self._lifestyle_app_visibility_domain()
            + [('sale_ok', '=', True), ('active', '=', True), ('color_options', '!=', False)]
        )
        colors = set()
        for product in products:
            colors.update(value.strip() for value in (product.color_options or '').split(',') if value.strip())
        return sorted(colors)

    @api.model
    def _lifestyle_available_rooms(self):
        products = self.sudo().search(
            self._lifestyle_app_visibility_domain()
            + [('sale_ok', '=', True), ('active', '=', True), ('lifestyle_room_ids', '!=', False)]
        )
        room_ids = products.mapped('lifestyle_room_ids').sorted('sequence')
        seen = set()
        rooms = []
        for room in room_ids:
            if room.id not in seen:
                seen.add(room.id)
                rooms.append((room.id, room.name))
        return rooms
    def _lifestyle_available_sizes(self):
        products = self.sudo().search(
            self._lifestyle_app_visibility_domain()
            + [('sale_ok', '=', True), ('active', '=', True), ('size_options', '!=', False)]
        )
        sizes = set()
        for product in products:
            sizes.update(value.strip() for value in (product.size_options or '').split(',') if value.strip())
        return sorted(sizes)

    @api.model
    def _lifestyle_available_years(self):
        """Years products were added to the store (create_date), newest
        first, for the "Year" shop filter."""
        products = self.sudo().search(
            self._lifestyle_app_visibility_domain() + [('sale_ok', '=', True), ('active', '=', True)]
        )
        years = {product.create_date.year for product in products if product.create_date}
        return sorted(years, reverse=True)
    # Image (not Binary) so Odoo auto-resizes/compresses on upload instead of
    # storing whatever full-camera-resolution file the admin picked - that
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

    lifestyle_deal_ends_at = fields.Datetime(
        string='Flash Deal Ends At',
        help=(
            'Optional. Requires Compare at Price to be higher than Price. '
            'While set in the future, this product appears in the app\'s Flash Deals '
            'carousel with a countdown until this time.'
        ),
    )

    # ── Christian Revive app (OneVoice27) store settings ──────────────────
    # The Christian Revive app's Store tab already reads products flagged
    # with is_store_product (defined in volunteer_and_donation_management),
    # so that same field - relabeled "Show in Christian Revive App" on the
    # product form - drives both the app and the /christianrevive website.
    # Physical product data (color images, reviews, rooms) is shared
    # between both brands; only behavior is per-app.
    cr_deal_ends_at = fields.Datetime(
        string='Christian Revive Deal Ends At',
        help=(
            'Optional. Requires Compare at Price to be higher than Price. '
            'While set in the future, this product appears in the Christian Revive '
            'app\'s Flash Deals carousel with a countdown until this time.'
        ),
    )
    cr_store_image_2_product_id = fields.Many2one(
        'product.template', string='CR Image 2 Links To Product',
        help='Optional. If set, tapping this photo in the Christian Revive app opens that product page instead of zooming in.',
    )
    cr_store_image_3_product_id = fields.Many2one(
        'product.template', string='CR Image 3 Links To Product',
        help='Optional. If set, tapping this photo in the Christian Revive app opens that product page instead of zooming in.',
    )
    cr_store_image_4_product_id = fields.Many2one(
        'product.template', string='CR Image 4 Links To Product',
        help='Optional. If set, tapping this photo in the Christian Revive app opens that product page instead of zooming in.',
    )

    @api.model
    def _cr_app_visibility_domain(self):
        """Catalog domain for the Christian Revive app / website.

        Matches what the OneVoice27 app's Store tab already queries."""
        return [('is_store_product', '=', True)]

    def action_optimize_lifestyle_images(self):
        """Re-saves every image field on these products through itself,
        which makes Odoo re-run the Image field's resize/compression step -
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
