# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OnevoiceDoaChapter(models.Model):
    _name        = 'onevoice.doa.chapter'
    _description = 'Desire of Ages — Chapter'
    _order       = 'chapter_number'

    chapter_number = fields.Integer(string='Chapter #', required=True)
    title_en       = fields.Char(string='English Title',  required=True)
    text_en        = fields.Text(string='English Text',   required=True)
    title_ur       = fields.Char(string='Urdu Title')
    text_ur        = fields.Text(string='Urdu Text')
    is_published   = fields.Boolean(string='Published', default=True)
    notes          = fields.Char(string='Admin Notes')

    _sql_constraints = [
        ('chapter_number_uniq', 'unique(chapter_number)',
         'A chapter with this number already exists.'),
    ]

    @api.model
    def app_get_chapter(self, chapter_number):
        """Return one chapter as a dict for the Flutter app.
        Returns False if the chapter does not exist or is not published."""
        record = self.sudo().search([
            ('chapter_number', '=', chapter_number),
            ('is_published',   '=', True),
        ], limit=1)
        if not record:
            return False
        return {
            'chapter_number': record.chapter_number,
            'title_en':       record.title_en  or '',
            'text_en':        record.text_en   or '',
            'title_ur':       record.title_ur  or '',
            'text_ur':        record.text_ur   or '',
        }

    @api.model
    def app_get_published_chapter_numbers(self):
        """Return list of chapter numbers that have Odoo content, so the
        Flutter app knows which chapters to fetch vs fall back to JSON."""
        records = self.sudo().search([('is_published', '=', True)])
        return sorted(r.chapter_number for r in records)
