from odoo import fields, models

class MinistryPartner(models.Model):
    _name = 'ministry.partner'
    _description = 'Ministry Partner'
    _order = 'create_date desc'

    name = fields.Char(string='Full Name / Organization', required=True)
    contact_person = fields.Char(string='Contact Person')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone / WhatsApp')
    country_id = fields.Many2one('res.country', string='Country')
    city = fields.Char(string='City')
    organization_name = fields.Char(string='Organization Name')
    website = fields.Char(string='Website / Social Media')

    partner_type = fields.Selection([
        ('individual', 'Individual'),
        ('church', 'Church'),
        ('ngo', 'NGO / Organization'),
        ('corporate', 'Corporate Partner'),
    ], string='Partner Type', default='individual')

    partnership_areas = fields.Many2many(
        'ministry.partner.area', string='Areas of Partnership Interest')

    contribution_type = fields.Selection([
        ('one_time', 'One-time'),
        ('monthly', 'Monthly'),
        ('project_based', 'Project-based'),
    ], string='Contribution Type')

    estimated_support = fields.Text(string='Estimated Support')

    motivation = fields.Text(string='Why do you want to partner with us?')
    faith_agreement = fields.Boolean(string='Agrees with Mission & Values', default=False)

    experience = fields.Text(string='Previous Partnership Experience')
    skills = fields.Many2many('ministry.partner.skill', string='Skills / Expertise')
    resources = fields.Text(string='Resources You Can Provide')

    registration_number = fields.Char(string='Registration Number')
    ntn = fields.Char(string='Tax ID / NTN')
    agreement_accepted = fields.Boolean(string='Accepts Terms & Conditions', default=False)

    communication_preference = fields.Selection([
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('phone', 'Phone'),
    ], string='Preferred Contact Method', default='whatsapp')

    update_frequency = fields.Selection([
        ('monthly', 'Monthly Updates'),
        ('quarterly', 'Quarterly Reports'),
    ], string='Update Frequency', default='monthly')

    linked_partner_id = fields.Many2one('res.partner', string='Linked Contact')

    status = fields.Selection([
        ('new', 'New'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='new')

    image = fields.Binary(string='Photo')


class MinistryPartnerArea(models.Model):
    _name = 'ministry.partner.area'
    _description = 'Partnership Area'

    name = fields.Char(string='Area Name', required=True)
    code = fields.Char(string='Code')


class MinistryPartnerSkill(models.Model):
    _name = 'ministry.partner.skill'
    _description = 'Partner Skill'

    name = fields.Char(string='Skill Name', required=True)
    code = fields.Char(string='Code')