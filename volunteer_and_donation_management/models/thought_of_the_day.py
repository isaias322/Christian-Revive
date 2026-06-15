from odoo import fields, models

class ThoughtOfTheDay(models.Model):
    _name = 'thought.of.the.day'
    _description = 'Thought of the Day'

    name = fields.Char(string='Title', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    content = fields.Html(string='Content')
    summary = fields.Text(string='Summary')
    image = fields.Binary(string='Image', attachment=True)
    is_published = fields.Boolean(string='Published', default=False)
    day_number = fields.Integer(string='Day Number', default=1)

    video = fields.Binary(string='Video', attachment=True)
    video_url = fields.Char(string='Video URL')

    # ── Source ──────────────────────────────────
    source_type = fields.Selection([
        ('video', 'Video (YouTube / Upload)'),
        ('cloud', 'Cloud Video (Drive/OneDrive)'),
        ('audio', 'Upload MP3'),
    ], string='Media Source', default='video', required=True)
    cloud_video_url = fields.Char(string='Cloud Video Link')
    audio_file = fields.Binary(string='MP3 File', attachment=True)
    audio_filename = fields.Char(string='MP3 Filename')

    def action_publish(self):
        self.write({'is_published': True})

    def action_unpublish(self):
        self.write({'is_published': False})