from odoo import fields, models

class HrEmployeeExtended(models.Model):
    _inherit = 'hr.employee'

    # Role in the church/clinic
    staff_role = fields.Selection([
        ('pastor',  'Pastor'),
        ('doctor',  'Doctor'),
        ('nurse',   'Nurse'),
        ('admin',   'Admin Staff'),
        ('other',   'Other'),
    ], string='Staff Role')

    # App login credentials
    app_pin = fields.Char(string='App PIN (4-6 digits)')
    app_email = fields.Char(string='App Login Email')
    is_app_active = fields.Boolean(string='App Access Active', default=True)