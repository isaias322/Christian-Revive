from odoo import models, fields

class HrEmployeeExtended(models.Model):
    _inherit = 'hr.employee'

    staff_role = fields.Selection([
        ('pastor', 'Pastor'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('admin','Project Admin'),  # ← renamed
        ('other', 'Other'),
    ], string='Staff Role')

    app_pin        = fields.Char(string='App PIN (4-6 digits)')
    app_email      = fields.Char(string='App Login Email')
    is_app_active  = fields.Boolean(string='App Access Active', default=True)

    # ── Project assignment (for admin role) ──────────────
    assigned_project_ids = fields.Many2many(
        'app.project',
        string='Assigned Projects',
        domain=[('is_active', '=', True)],
    )