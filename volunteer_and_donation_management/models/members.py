from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_member = fields.Boolean(string="Member")

    date_of_birth = fields.Date(string="Date of Birth")
    cnic = fields.Char(string="CNIC")

    membership_type = fields.Selection([
        ('monthly', 'Monthly Member'),
        ('annual', 'Annual Member'),
        ('lifetime', 'Lifetime Member')
    ], string="Membership Type")

    contribution_preference = fields.Selection([
        ('financial', 'Financial Support'),
        ('event', 'Event Support'),
        ('administrative', 'Administrative Support')
    ], string="Contribution Preference")