# models/daily_verse.py
from odoo import models, fields

class DailyVerse(models.Model):
    _name = 'church.daily.verse'
    _description = 'Daily Bible Verse'
    _order = 'scheduled_date desc'

    scheduled_date = fields.Date(string='Show on Date', required=True)
    reference = fields.Char(string='Bible Reference', required=True, help='e.g. John 3:16')
    verse_text = fields.Text(string='Verse Text', required=True)
    theme = fields.Char(string='Theme', required=True, help='One word e.g. Hope, Faith, Love')
    source = fields.Selection([
        ('manual', 'Added by Pastor'),
        ('auto_ai', 'Auto Generated'),
    ], string='Source', default='manual')
    is_active = fields.Boolean(default=True)