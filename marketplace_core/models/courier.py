# -*- coding: utf-8 -*-
from odoo import fields, models


class MarketplaceCourier(models.Model):
    _name = 'marketplace.courier'
    _description = 'Marketplace Courier'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    code = fields.Selection([
        ('tcs', 'TCS'),
        ('leopards', 'Leopards'),
        ('mnp', 'M&P'),
        ('bluex', 'BlueEx'),
        ('other', 'Other'),
    ], required=True, default='other')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    supports_cod = fields.Boolean(string='Supports COD', default=True)
    tracking_url_pattern = fields.Char(
        help='URL pattern for shipment tracking. Use {tracking} as the '
             'placeholder for the tracking number, e.g. '
             'https://www.tcsexpress.com/track/?tracking={tracking}')
    api_base_url = fields.Char(
        string='API Base URL',
        help='Base URL of the courier booking API (label generation).')
    api_key = fields.Char(string='API Key', groups='marketplace_core.group_marketplace_manager')
    flat_rate = fields.Float(
        string='Flat Shipping Rate',
        help='Default shipping charge applied at checkout for this courier.')

    def get_tracking_url(self, tracking_number):
        self.ensure_one()
        if self.tracking_url_pattern and tracking_number:
            return self.tracking_url_pattern.replace('{tracking}', tracking_number)
        return False
