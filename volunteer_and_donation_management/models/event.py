from odoo import fields, models, api

class ChurchEvent(models.Model):
    _name = 'church.event'
    _description = 'Church Event'
    _order = 'date_start asc'

    name = fields.Char(string='Event Name', required=True)
    description = fields.Text(string='Description')
    content = fields.Html(string='Content')
    date_start = fields.Datetime(string='Start Date', required=True)
    date_end = fields.Datetime(string='End Date')
    location = fields.Char(string='Location')
    image = fields.Binary(string='Image')
    video_url = fields.Char(string='Video URL (YouTube)')
    video = fields.Binary(string='Video File')
    is_published = fields.Boolean(string='Published', default=True)
    category = fields.Selection([
        ('meeting', 'Meeting'),
        ('worship', 'Worship'),
        ('conference', 'Conference'),
        ('youth', 'Youth'),
        ('prayer', 'Prayer'),
        ('other', 'Other'),
    ], string='Category', default='other')

    # Simpler approach — just add to your existing model:
    has_image = fields.Boolean(
        string='Has Image', 
        compute='_compute_has_image', 
        store=True
    )

    @api.depends('image')
    def _compute_has_image(self):
        for rec in self:
            rec.has_image = bool(rec.image)