from odoo import models, fields


class DailyDevotional(models.Model):
    _name = 'daily.devotional'
    _description = 'Daily Devotional'
    _order = 'date desc'

    # ✅ Required for Odoo 19 JSON-2 API access
    # This allows external API calls to this model
    _allow_sudo_commands = False  # set True only if you need sudo access

    name = fields.Char(string='Title', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    content = fields.Html(string='Content')
    summary = fields.Text(string='Summary')
    scripture_reference = fields.Char(string='Scripture Reference')
    author = fields.Char(string='Author')
    image = fields.Binary(string='Image', attachment=True)
    is_published = fields.Boolean(string='Published', default=False)
    category = fields.Selection([
        ('morning', 'Morning Devotional'),
        ('evening', 'Evening Devotional'),
        ('special', 'Special'),
    ], string='Category', default='morning')

    video = fields.Binary(string='Video', attachment=True)
    video_url = fields.Char(string='Video URL')

    def action_publish(self):
        self.write({'is_published': True})

    def action_unpublish(self):
        self.write({'is_published': False})