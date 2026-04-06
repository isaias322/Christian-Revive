from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_volunteer = fields.Boolean(string="Volunteer")

    date_of_birth = fields.Date(string="Date of Birth")

    cnic = fields.Char(string="CNIC")

    volunteer_skill = fields.Many2many(
        'volunteer.skill',
        string="Volunteer Skills"
    )

    availability = fields.Selection([
        ('part_time', 'Part Time'),
        ('weekends', 'Weekends Only'),
        ('custom', 'Custom Days')
    ], string="Availability")

    motivation = fields.Text(string="Motivation")

class VolunteerDepartment(models.Model):
    _name = 'volunteer.department'
    _description = 'Volunteer Department'

    name = fields.Char(string="Department Name", required=True)


class VolunteerSkills(models.Model):
    _name = 'volunteer.skills'
    _description = 'Volunteer Skills'

    name = fields.Char(string="Skill Name", required=True)