from odoo import models, fields

class HealthBroadcast(models.Model):
    _name = 'health.broadcast'
    _description = 'Health Broadcast'
    _order = 'date desc'

    name = fields.Char(string='Title', required=True)
    description = fields.Text(string='Description')
    date = fields.Date(string='Date', default=fields.Date.today)
    category = fields.Selection([
        ('nutrition', 'Nutrition'),
        ('mental', 'Mental Health'),
        ('fitness', 'Fitness'),
        ('medical', 'Medical'),
        ('prayer', 'Prayer & Healing'),
        ('general', 'General'),
    ], string='Category', default='general')
    video_url = fields.Char(string='YouTube URL')
    image = fields.Binary(string='Thumbnail')
    is_published = fields.Boolean(string='Published', default=True)
    duration = fields.Char(string='Duration (e.g. 12:34)')
    presenter = fields.Char(string='Presenter')