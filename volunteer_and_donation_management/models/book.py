from odoo import fields, models

class Book(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _order = 'sequence, date desc'

    sequence = fields.Integer(string='Sequence')
    name = fields.Char(string='Title', required=True)
    author = fields.Char(string='Author')
    date = fields.Date(string='Published Date')
    description = fields.Text(string='Description')
    content = fields.Html(string='Content')
    image = fields.Binary(string='Cover Image')
    pdf_file = fields.Binary(string='PDF File')
    pdf_filename = fields.Char(string='PDF Filename')
    is_published = fields.Boolean(string='Published', default=True)
    category = fields.Selection([
        ('bible_study', 'Bible Study'),
        ('devotional', 'Devotional'),
        ('theology', 'Theology'),
        ('history', 'History'),
        ('youth', 'Youth'),
        ('other', 'Other'),
    ], string='Category', default='other')