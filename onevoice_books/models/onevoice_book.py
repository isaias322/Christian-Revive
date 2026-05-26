# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OnevoiceBook(models.Model):
    _name        = 'onevoice.book'
    _description = 'App Book'
    _order       = 'sequence, name'

    name        = fields.Char(string='Book Title',  required=True)
    book_code   = fields.Char(string='Book Code',   required=True,
                               help='Unique identifier used by the app (e.g. desire_of_ages, patriarchs_prophets). '
                                    'Use lowercase letters and underscores only. Do NOT change after publishing.')
    author      = fields.Char(string='Author')
    description = fields.Text(string='Description')
    sequence    = fields.Integer(string='Order', default=10)
    is_published = fields.Boolean(string='Published', default=True)
    chapter_ids  = fields.One2many('onevoice.book.chapter', 'book_id', string='Chapters')
    chapter_count = fields.Integer(string='Chapters', compute='_compute_chapter_count')

    _sql_constraints = [
        ('book_code_uniq', 'unique(book_code)',
         'A book with this code already exists.'),
    ]

    @api.depends('chapter_ids')
    def _compute_chapter_count(self):
        for rec in self:
            rec.chapter_count = len(rec.chapter_ids)

    @api.model
    def app_get_books(self):
        """Return all published books as a list of dicts for the app."""
        records = self.sudo().search([('is_published', '=', True)])
        return [{
            'id':          r.id,
            'book_code':   r.book_code,
            'name':        r.name,
            'author':      r.author or '',
            'description': r.description or '',
            'sequence':    r.sequence,
        } for r in records]

    @api.model
    def app_get_published_chapter_numbers(self, book_code):
        """Return sorted list of published chapter numbers for a given book_code."""
        book = self.sudo().search([
            ('book_code',   '=', book_code),
            ('is_published', '=', True),
        ], limit=1)
        if not book:
            return []
        chapters = self.env['onevoice.book.chapter'].sudo().search([
            ('book_id',     '=', book.id),
            ('is_published', '=', True),
        ])
        return sorted(c.chapter_number for c in chapters)

    @api.model
    def app_get_chapter(self, book_code, chapter_number):
        """Return one chapter dict for the app, or False if not found."""
        book = self.sudo().search([
            ('book_code',   '=', book_code),
            ('is_published', '=', True),
        ], limit=1)
        if not book:
            return False
        chapter = self.env['onevoice.book.chapter'].sudo().search([
            ('book_id',        '=', book.id),
            ('chapter_number', '=', chapter_number),
            ('is_published',   '=', True),
        ], limit=1)
        if not chapter:
            return False
        return {
            'chapter_number': chapter.chapter_number,
            'title_en':       chapter.title_en or '',
            'text_en':        chapter.text_en  or '',
            'title_ur':       chapter.title_ur or '',
            'text_ur':        chapter.text_ur  or '',
        }
