from odoo import models, fields

class VolunteerSkill(models.Model):
    _name = "volunteer.skill"
    _description = "Volunteer Skill"

    name = fields.Char(string="Volunteer Skill", required=True)
    code = fields.Char(string="Volunteer Skill Code")
    color = fields.Integer(string="Color")