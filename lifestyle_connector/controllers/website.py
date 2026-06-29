# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class LifestyleWebsite(http.Controller):

    @http.route(['/contactus', '/contact-us'], type='http', auth='public', website=True, sitemap=True)
    def contactus(self, **kwargs):
        return request.render('lifestyle_connector.lifestyle_contactus_direct_page', {})