# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OnevoiceRomanOverride(models.Model):
    _name        = 'onevoice.roman.override'
    _description = 'Roman Urdu Override'
    _order       = 'source_text'

    source_text = fields.Char(string='English Text',        required=True)
    roman_text  = fields.Char(string='Roman Urdu',          required=True)
    notes       = fields.Char(string='Notes (optional)',    help='Admin reference — e.g. "used in Gospel quiz Q3"')
    is_active   = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('source_text_uniq', 'unique(source_text)',
         'A Roman Urdu override for this English text already exists.'),
    ]

    @api.model
    def app_get_roman_translations(self):
        """Return all active Roman Urdu overrides as a flat {english: roman} dict for the Flutter app."""
        records = self.sudo().search([('is_active', '=', True)])
        return {r.source_text: r.roman_text for r in records}
