# -*- coding: utf-8 -*-
from urllib.parse import urlparse

from odoo import api, fields, models
from odoo.http import request


def _rl_is_lifestyle_path(path):
    return (
        path == '/'
        or path == '/shop'
        or path.startswith('/shop/page')
        or path.startswith('/shop/category')
        or path.startswith('/contactus')
        or path.startswith('/contact-us')
    )


def _rl_is_market_path(path):
    return path == '/market' or path.startswith('/market/')


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _pre_dispatch(cls, rule, args):
        """Keep the storefront-brand session flag fresh on every request.

        Controller-level stamping alone misses navigations served from the
        browser cache. Storefront pages stamp by path; entering the shared
        account/cart area stamps by referrer, so 'My Account' clicked on
        the Lifestyle site opens in Lifestyle and clicked on the Christian
        Revive site opens in CR."""
        super()._pre_dispatch(rule, args)
        try:
            path = request.httprequest.path
            # Explicit brand marker in the URL wins - it survives the
            # session reset Odoo performs on login (the redirect target
            # carries it through the auth flow).
            brand_param = request.httprequest.args.get('rl_brand')
            if brand_param in ('cr', 'lifestyle', 'market'):
                request.session['rl_web_brand'] = brand_param
                return
            # Real second website: any path reached via the Christian
            # Revive domain is CR-branded, even a shared path like /shop
            # that would otherwise path-match as Lifestyle - a visitor
            # arriving straight at shop.christianrevive.org/shop (not via
            # the homepage first) must still get CR branding.
            site = getattr(request, 'website', False)
            if site and site.domain and 'christianrevive' in site.domain.lower():
                request.session['rl_web_brand'] = 'cr'
                return
            if path.startswith('/christianrevive'):
                request.session['rl_web_brand'] = 'cr'
            elif _rl_is_market_path(path):
                request.session['rl_web_brand'] = 'market'
            elif _rl_is_lifestyle_path(path):
                request.session['rl_web_brand'] = 'lifestyle'
            elif path.startswith('/my') or path.startswith('/shop/cart'):
                referrer = request.httprequest.referrer or ''
                referrer_path = urlparse(referrer).path if referrer else ''
                if '/christianrevive' in referrer:
                    request.session['rl_web_brand'] = 'cr'
                elif _rl_is_market_path(referrer_path):
                    request.session['rl_web_brand'] = 'market'
                elif referrer and _rl_is_lifestyle_path(referrer_path):
                    request.session['rl_web_brand'] = 'lifestyle'
        except Exception:
            pass


class Website(models.Model):
    """Keeps the public shop restricted to the same products the Revive
    Lifestyle app shows. Odoo's own product_domain only filters by
    published-state for non-staff visitors, so an internal/admin preview
    (and any other product in this shared database) would otherwise leak
    through onto this storefront."""
    _inherit = 'website'

    @api.model
    def _rl_apply_lifestyle_branding(self):
        """Re-applies the Lifestyle logo/favicon on every module upgrade.

        Written to find the right website record(s) dynamically rather
        than assume website.default_website is the one actually serving
        traffic - once a second, hand-created website record existed
        (e.g. for a real custom domain), a hard-coded xmlid was silently
        updating the WRONG record and the live site never changed."""
        import base64
        from odoo.modules.module import get_resource_path

        sites = self.sudo().search([]).filtered(
            lambda site: not (site.domain and 'christianrevive' in site.domain.lower())
        )
        if not sites:
            return
        logo_path = get_resource_path(
            'lifestyle_connector', 'static', 'src', 'img', 'revive_lifestyle_logo.png')
        favicon_path = get_resource_path(
            'lifestyle_connector', 'static', 'src', 'img', 'app_icon.png')
        vals = {}
        if logo_path:
            with open(logo_path, 'rb') as f:
                vals['logo'] = base64.b64encode(f.read())
        if favicon_path:
            with open(favicon_path, 'rb') as f:
                vals['favicon'] = base64.b64encode(f.read())
        if vals:
            sites.write(vals)

    def _product_domain(self):
        domain = super()._product_domain()
        Product = self.env['product.template']
        # The Lifestyle /shop grid lists only the Lifestyle catalog - but
        # everything else that consults this domain (the product page's
        # add-to-cart possibility check, cart validation) must accept
        # products of EITHER storefront: the Christian Revive store sells
        # through the same product pages and cart. Restricting those to
        # Lifestyle-only made CR-only products show "no valid combination".
        path = request.httprequest.path if request else ''
        is_shop_listing = (
            path == '/shop'
            or path.startswith('/shop/page')
            or path.startswith('/shop/category')
        )
        if is_shop_listing:
            domain = domain + Product._lifestyle_app_visibility_domain()
        else:
            domain = (
                domain + ['|']
                + Product._lifestyle_app_visibility_domain()
                + Product._cr_app_visibility_domain()
            )

        # color_options/size_options are plain comma-separated Char fields,
        # not real Odoo attributes, so the native attribute filters can't
        # see them - the shop's color/size filter links read these instead.
        color = request.params.get('lifestyle_color')
        if color:
            domain = domain + [('color_options', 'ilike', color)]
        size = request.params.get('lifestyle_size')
        if size:
            domain = domain + [('size_options', 'ilike', size)]

        room = request.params.get('lifestyle_room')
        if room:
            domain = domain + [('lifestyle_room_ids', 'in', [int(room)])]

        quick = request.params.get('lifestyle_quick')
        if quick == 'new':
            domain = domain + [('create_date', '>=', fields.Datetime.subtract(fields.Datetime.now(), days=45))]
        elif quick == 'popular':
            sold_lines = self.env['sale.order.line'].sudo().search([
                ('order_id.state', 'in', ('sale', 'done')),
                ('product_id.product_tmpl_id', '!=', False),
            ])
            sold_template_ids = sold_lines.mapped('product_id.product_tmpl_id').ids
            domain = domain + [('id', 'in', sold_template_ids or [0])]
        availability = request.params.get('lifestyle_availability')
        if availability in ('in_stock', 'out_of_stock'):
            # qty_available in a public-user domain triggers an AccessError
            # (computing it reads stock.warehouse, which visitors can't).
            # Precompute the in-stock ids with sudo and filter by id.
            stockable = self.env['product.template'].sudo().search(
                [('is_storable', '=', True), ('sale_ok', '=', True)])
            in_stock_ids = stockable.filtered(lambda p: p.qty_available > 0).ids
            if availability == 'in_stock':
                domain = domain + ['|', ('is_storable', '=', False), ('id', 'in', in_stock_ids or [0])]
            else:
                domain = domain + [('is_storable', '=', True), ('id', 'not in', in_stock_ids or [0])]

        year = request.params.get('lifestyle_year')
        if year:
            year = int(year)
            domain = domain + [
                ('create_date', '>=', f'{year}-01-01 00:00:00'),
                ('create_date', '<', f'{year + 1}-01-01 00:00:00'),
            ]
        return domain
