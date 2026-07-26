# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

LISTING_CONDITIONS = [
    ('new_with_tags', 'New with tags'),
    ('new_without_tags', 'New without tags'),
    ('very_good', 'Very good'),
    ('good', 'Good'),
    ('satisfactory', 'Satisfactory'),
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_marketplace_listing = fields.Boolean(
        string='Marketplace Listing', default=False, index=True)
    marketplace_seller_id = fields.Many2one(
        'marketplace.seller', string='Seller Shop', index=True,
        ondelete='cascade')
    listing_state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('active', 'Active'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('rejected', 'Rejected'),
        ('removed', 'Archived'),
    ], default='draft', tracking=True, index=True)
    condition = fields.Selection(
        LISTING_CONDITIONS, string='Condition')
    marketplace_brand_id = fields.Many2one(
        'marketplace.brand', string='Brand')
    marketplace_size_id = fields.Many2one(
        'marketplace.size', string='Size')
    color = fields.Char(string='Colour')
    material = fields.Char()
    original_price = fields.Float(
        help='What the item cost new (optional, shown crossed out).')
    discount_pct = fields.Float(
        string='Discount %', default=0.0,
        help='Set together with Original Price to have the sale price '
             '(list_price) calculated automatically: '
             'list_price = original_price * (1 - discount_pct / 100).')
    rejection_reason = fields.Text()
    removed_by_suspension = fields.Boolean(
        default=False, copy=False,
        help='Set when this listing was auto-removed because the seller '
             'shop was suspended, so reactivating the shop knows to '
             'restore exactly these listings and not ones the seller '
             'had already taken down themselves.')
    stock_quantity = fields.Integer(
        string='Quantity Available', default=1,
        help='How many identical units the seller has. Buying one '
             'reduces this by one; the listing keeps selling to other '
             'buyers until stock runs out, instead of delisting after '
             'a single sale.')

    view_count = fields.Integer(default=0, copy=False)
    favorite_partner_ids = fields.Many2many(
        'res.partner', 'marketplace_listing_favorite_rel',
        'product_tmpl_id', 'partner_id', string='Favourited By', copy=False)
    favorite_count = fields.Integer(compute='_compute_favorite_count')

    bump_until = fields.Datetime(
        string='Bumped Until', copy=False,
        help='Paid promotion: listing ranks first in search until this date.')
    is_bumped = fields.Boolean(compute='_compute_is_bumped', search='_search_is_bumped')

    is_verified_item = fields.Boolean(
        string='Verified Item',
        help='Item passed the marketplace item-verification service.')

    def _compute_favorite_count(self):
        for tmpl in self:
            tmpl.favorite_count = len(tmpl.favorite_partner_ids)

    @api.depends('bump_until')
    def _compute_is_bumped(self):
        now = fields.Datetime.now()
        for tmpl in self:
            tmpl.is_bumped = bool(tmpl.bump_until and tmpl.bump_until > now)

    def _search_is_bumped(self, operator, value):
        now = fields.Datetime.now()
        domain = [('bump_until', '>', now)]
        if (operator == '=' and not value) or (operator == '!=' and value):
            domain = ['|', ('bump_until', '=', False), ('bump_until', '<=', now)]
        return domain

    @api.constrains('is_marketplace_listing', 'marketplace_seller_id')
    def _check_marketplace_seller(self):
        for tmpl in self:
            if tmpl.is_marketplace_listing and not tmpl.marketplace_seller_id:
                raise ValidationError(_(
                    'A marketplace listing must belong to a seller shop.'))

    @api.constrains('discount_pct')
    def _check_discount_pct(self):
        for tmpl in self:
            if not 0 <= tmpl.discount_pct <= 95:
                raise ValidationError(_(
                    'Discount must be between 0 and 95%.'))

    # ------------------------------------------------------------------
    # Discount: sale price is calculated automatically, not typed in
    # ------------------------------------------------------------------
    @api.onchange('discount_pct', 'original_price')
    def _onchange_discount_pct(self):
        for tmpl in self:
            if tmpl.original_price and tmpl.discount_pct:
                tmpl.list_price = round(
                    tmpl.original_price * (1 - tmpl.discount_pct / 100.0), 2)

    def _recompute_discounted_price(self):
        for tmpl in self:
            if tmpl.original_price and tmpl.discount_pct:
                new_price = round(
                    tmpl.original_price * (1 - tmpl.discount_pct / 100.0), 2)
                if tmpl.list_price != new_price:
                    tmpl.list_price = new_price

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._recompute_discounted_price()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'discount_pct' in vals or 'original_price' in vals:
            self._recompute_discounted_price()
        return res

    # ------------------------------------------------------------------
    # Moderation / lifecycle
    # ------------------------------------------------------------------
    def _check_banned_content(self):
        Banned = self.env['marketplace.banned.keyword'].sudo()
        for tmpl in self:
            match = Banned._find_match(tmpl.name, tmpl.description_sale)
            if match:
                raise UserError(_(
                    'This listing cannot be published: it matches the banned '
                    'item policy ("%(keyword)s"%(reason)s).',
                    keyword=match.name,
                    reason=match.reason and ': %s' % match.reason or ''))

    def _needs_manual_review(self):
        """Basic fraud/trust heuristics, on top of the banned-keyword
        check — flagged listings still publish once a moderator approves
        them, they just don't skip the queue via auto-approval. Neither
        rule is about the item being bad; both are common early signals
        real marketplaces use to catch counterfeits and account-takeover/
        scam listings before they go live."""
        self.ensure_one()
        if self.marketplace_brand_id.is_luxury:
            # Counterfeits concentrate in luxury brands — Vinted-style
            # platforms specifically call this out as needing item
            # verification before a high-value "designer" listing is
            # trusted at face value.
            return True
        HIGH_VALUE = 20000.0
        if (self.list_price >= HIGH_VALUE
                and self.marketplace_seller_id.sold_listing_count == 0):
            # A brand-new seller's first listing being high-value is a
            # classic pattern for scam/never-ship listings — not a
            # judgement on the seller, just worth a human glance first.
            return True
        return False

    def action_submit_listing(self):
        for tmpl in self:
            if not tmpl.is_marketplace_listing:
                continue
            if tmpl.listing_state not in ('draft', 'rejected', 'removed'):
                raise UserError(_('Only draft listings can be submitted.'))
            if tmpl.list_price <= 0:
                raise UserError(_('Please set a price before publishing.'))
            if tmpl.stock_quantity <= 0:
                raise UserError(_(
                    'Please set how many you have in stock before '
                    'publishing.'))
            tmpl._check_banned_content()
            moderate = self.env['ir.config_parameter'].sudo().get_param(
                'marketplace_core.moderate_listings')
            if moderate or tmpl._needs_manual_review():
                tmpl.listing_state = 'pending'
            else:
                tmpl.action_approve_listing()

    def action_approve_listing(self):
        self._check_banned_content()
        self.write({'listing_state': 'active', 'is_published': True})

    def action_reject_listing(self, reason=None):
        self.write({
            'listing_state': 'rejected',
            'is_published': False,
            'rejection_reason': reason or self.env.context.get('rejection_reason'),
        })

    def action_mark_reserved(self):
        """Called once per unit when an order for it is confirmed. Stock
        is decremented immediately; a listing with more than one unit
        keeps selling to other buyers and only stops being independently
        buyable once it actually runs out."""
        for tmpl in self.filtered(lambda t: t.listing_state == 'active'):
            tmpl.stock_quantity -= 1
            if tmpl.stock_quantity <= 0:
                tmpl.listing_state = 'reserved'

    def action_mark_sold(self):
        """Called when escrow releases for a unit. Only fully delists
        the listing once stock is actually exhausted — releasing escrow
        on one unit of a multi-quantity listing shouldn't pull the
        still-available units off the market."""
        self.filtered(lambda t: t.stock_quantity <= 0).write(
            {'listing_state': 'sold', 'is_published': False})

    def action_relist(self):
        self.filtered(
            lambda t: t.listing_state in ('reserved', 'removed')
        ).write({
            'listing_state': 'active', 'is_published': True,
            'removed_by_suspension': False,
        })

    def action_remove_listing(self):
        self.write({'listing_state': 'removed', 'is_published': False})

    def action_delete_listing(self):
        """Permanently delete. Active/reserved/sold listings must be
        archived first — reserved and sold ones may already be referenced
        by a real order, and archiving an active one first gives the
        seller an undo path instead of an irreversible click."""
        blocked = self.filtered(
            lambda t: t.listing_state in ('active', 'reserved', 'sold'))
        if blocked:
            raise UserError(_(
                'Archive "%(name)s" before deleting it — active, reserved, '
                'or sold listings can\'t be deleted directly.',
                name=blocked[0].name))
        self.unlink()

    def action_bump(self, days=7):
        """Paid promotion stub: rank first in search for `days` days."""
        until = fields.Datetime.add(fields.Datetime.now(), days=days)
        self.write({'bump_until': until})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def increment_view(self):
        # SQL to avoid write() side effects and stay cheap under load
        if self.ids:
            self.env.cr.execute(
                "UPDATE product_template SET view_count = "
                "COALESCE(view_count, 0) + 1 WHERE id IN %s",
                [tuple(self.ids)])
            self.invalidate_recordset(['view_count'])

    def is_favorited_by(self, partner):
        self.ensure_one()
        return bool(partner) and partner.id in self.favorite_partner_ids.ids

    def action_toggle_favorite(self, partner):
        self.ensure_one()
        if partner.id in self.favorite_partner_ids.ids:
            self.sudo().write({'favorite_partner_ids': [(3, partner.id)]})
            return False
        self.sudo().write({'favorite_partner_ids': [(4, partner.id)]})
        return True

    @api.model
    def marketplace_search_domain(self, filters=None):
        """Shared search-domain builder used by website + mobile API."""
        filters = filters or {}
        domain = [
            ('is_marketplace_listing', '=', True),
            ('listing_state', '=', 'active'),
            ('marketplace_seller_id.state', '=', 'approved'),
        ]
        if filters.get('search'):
            domain += ['|', '|',
                       ('name', 'ilike', filters['search']),
                       ('description_sale', 'ilike', filters['search']),
                       ('marketplace_brand_id.name', 'ilike', filters['search'])]
        if filters.get('category_id'):
            domain.append(
                ('public_categ_ids', 'child_of', int(filters['category_id'])))
        if filters.get('brand_id'):
            domain.append(
                ('marketplace_brand_id', '=', int(filters['brand_id'])))
        if filters.get('size_id'):
            domain.append(
                ('marketplace_size_id', '=', int(filters['size_id'])))
        if filters.get('condition'):
            domain.append(('condition', '=', filters['condition']))
        if filters.get('seller_id'):
            domain.append(
                ('marketplace_seller_id', '=', int(filters['seller_id'])))
        if filters.get('min_price'):
            domain.append(('list_price', '>=', float(filters['min_price'])))
        if filters.get('max_price'):
            domain.append(('list_price', '<=', float(filters['max_price'])))
        return domain

    @api.model
    def marketplace_sort_order(self, sort=None):
        return {
            'newest': 'bump_until desc nulls last, create_date desc',
            'price_asc': 'bump_until desc nulls last, list_price asc',
            'price_desc': 'bump_until desc nulls last, list_price desc',
            'popular': 'bump_until desc nulls last, view_count desc',
        }.get(sort or 'newest', 'bump_until desc nulls last, create_date desc')
