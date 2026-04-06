from odoo import fields, models

class SabbathSchoolLesson(models.Model):
    _name = 'sabbath.school.lesson'
    _description = 'Sabbath School Lesson'
    _order = 'date desc'

    name = fields.Char(string='Title', required=True)
    date = fields.Date(string='Date', required=True)
    quarter = fields.Selection([
        ('q1', 'Q1 (Jan-Mar)'),
        ('q2', 'Q2 (Apr-Jun)'),
        ('q3', 'Q3 (Jul-Sep)'),
        ('q4', 'Q4 (Oct-Dec)'),
    ], string='Quarter', required=True)
    year = fields.Char(string='Year', required=True)
    description = fields.Text(string='Description')
    content = fields.Html(string='Content')
    image = fields.Binary(string='Cover Image', attachment=True)
    pdf_file = fields.Binary(string='PDF Book', attachment=True)
    pdf_filename = fields.Char(string='PDF Filename')
    video_url = fields.Char(string='Video URL')
    is_published = fields.Boolean(string='Published', default=False)

    def action_publish(self):
        self.write({'is_published': True})

    def action_unpublish(self):
        self.write({'is_published': False})