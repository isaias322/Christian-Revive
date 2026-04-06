from odoo import models, fields

class AppProject(models.Model):
    _name = 'app.project'
    _description = 'App Project'
    _order = 'name asc'

    name = fields.Char(string='Project Name', required=True)
    description = fields.Text(string='Description')
    is_active = fields.Boolean(string='Active', default=True)
    project_type = fields.Selection([
        ('medical_camp', 'Medical Camp'),
        ('church',       'Church'),
        ('outreach',     'Outreach'),
        ('education',    'Education'),
        ('other',        'Other'),
    ], string='Type', default='other')
    color = fields.Integer(string='Color')