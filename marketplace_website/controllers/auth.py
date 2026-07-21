# -*- coding: utf-8 -*-
from odoo.http import request

from odoo.addons.web.controllers.home import Home


class MarketplaceHome(Home):
    """Buyers and sellers logging in with no explicit ?redirect= (e.g. the
    theme's generic "Sign in" link, or straight after signup) land on
    Odoo's generic /web/login_successful page — which reads like a bare
    account/profile screen and has nothing to do with the marketplace.
    Send non-internal (portal) users to the marketplace home instead;
    staff/admin logins and any explicit redirect are left untouched."""

    def _login_redirect(self, uid, redirect=None):
        if not redirect:
            user = request.env['res.users'].sudo().browse(uid)
            if not user._is_internal():
                return '/market'
        return super()._login_redirect(uid, redirect=redirect)
