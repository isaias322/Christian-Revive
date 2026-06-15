from odoo import fields, models

class Broadcast(models.Model):
    _name = 'broadcast'
    _description = 'Broadcast'

    name = fields.Char(string='Name', required=True)
    message = fields.Text(string='Message')
    date = fields.Datetime(string='Date', required=True)
    broadcast_section = fields.Selection([
        ('lessons_study_hour', 'Lessons Study Hour'),
        ('live_streaming', 'Live Streaming'),
        ('bible_answers', 'Bible Answers'),
        ('health_message', 'Health Message'),
    ], string='Broadcast Section')
    lessons = fields.Many2one('sabbath.school.lesson', string='Related Lessons')
    is_published = fields.Boolean(string='Published', default=False)

    image = fields.Binary(string='Image', attachment=True)
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