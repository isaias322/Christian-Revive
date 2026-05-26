# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DoaChapter(models.Model):
    _name        = 'onevoice.doa.chapter'
    _description = 'Desire of Ages — Chapter'
    _order       = 'chapter_number'

    chapter_number = fields.Integer(string='Chapter #', required=True)
    title_en       = fields.Char(string='English Title')
    text_en        = fields.Text(string='English Text')
    title_ur       = fields.Char(string='Urdu Title')
    text_ur        = fields.Text(string='Urdu Text')
    is_published   = fields.Boolean(string='Published', default=True)

    _sql_constraints = [
        ('chapter_number_uniq', 'unique(chapter_number)',
         'A chapter with this number already exists.'),
    ]

    @api.model
    def app_get_chapter(self, chapter_number):
        """Return one chapter as a dict for the Flutter app.
        Returns False if not found or not published."""
        rec = self.sudo().search([
            ('chapter_number', '=', chapter_number),
            ('is_published',   '=', True),
        ], limit=1)
        if not rec:
            return False
        return {
            'chapter_number': rec.chapter_number,
            'title_en':       rec.title_en or '',
            'text_en':        rec.text_en  or '',
            'title_ur':       rec.title_ur or '',
            'text_ur':        rec.text_ur  or '',
        }

    @api.model
    def app_get_published_numbers(self):
        """Return sorted list of published chapter numbers so the app knows
        which chapters are available in Odoo vs need JSON fallback."""
        recs = self.sudo().search([('is_published', '=', True)])
        return sorted(r.chapter_number for r in recs)
