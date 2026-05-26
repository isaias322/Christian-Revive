# -*- coding: utf-8 -*-
from odoo import models, fields


class OnevoiceBookChapter(models.Model):
    _name        = 'onevoice.book.chapter'
    _description = 'App Book Chapter'
    _order       = 'book_id, chapter_number'

    book_id        = fields.Many2one('onevoice.book', string='Book',
                                      required=True, ondelete='cascade')
    chapter_number = fields.Integer(string='Chapter #', required=True)
    title_en       = fields.Char(string='English Title')
    text_en        = fields.Text(string='English Text')
    title_ur       = fields.Char(string='Urdu Title')
    text_ur        = fields.Text(string='Urdu Text')
    is_published   = fields.Boolean(string='Published', default=True)
    notes          = fields.Char(string='Admin Notes')

    _sql_constraints = [
        ('book_chapter_uniq', 'unique(book_id, chapter_number)',
         'This chapter number already exists for this book.'),
    ]
