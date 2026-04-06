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

    def action_publish(self):
        self.write({'is_published': True})

    def action_unpublish(self):
        self.write({'is_published': False})