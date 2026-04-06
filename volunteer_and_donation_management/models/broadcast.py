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

    def action_publish(self):
        self.write({'is_published': True})

    def action_unpublish(self):
        self.write({'is_published': False})