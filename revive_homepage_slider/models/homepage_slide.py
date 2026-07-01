# -*- coding: utf-8 -*-
from odoo import fields, models


class ReviveHomepageSlide(models.Model):
    _name = 'lifestyle.homepage.slide'
    _description = 'Revive Website Hero Slide'
    _order = 'sequence, id'

    name = fields.Char(string='Internal Name', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    kicker = fields.Char(string='Small Heading', default='Revive Lifestyle Furniture')
    title = fields.Char(string='Main Title', required=True)
    subtitle = fields.Text(string='Description')
    image = fields.Binary(string='Hero Image')

    primary_button_label = fields.Char(string='Primary Button Label', default='Shop Furniture')
    primary_button_url = fields.Char(string='Primary Button URL', default='/shop')
    secondary_button_label = fields.Char(string='Secondary Button Label', default='Ask a Question')
    secondary_button_url = fields.Char(string='Secondary Button URL', default='/contactus')

    trust_1_icon = fields.Char(string='Trust 1 Icon', default='fa-check')
    trust_1_text = fields.Char(string='Trust 1 Text', default='Build tracking')
    trust_2_icon = fields.Char(string='Trust 2 Icon', default='fa-camera')
    trust_2_text = fields.Char(string='Trust 2 Text', default='Workshop updates')
    trust_3_icon = fields.Char(string='Trust 3 Icon', default='fa-truck')
    trust_3_text = fields.Char(string='Trust 3 Text', default='Delivery support')

    card_icon = fields.Char(string='Card Icon', default='fa-home')
    card_title = fields.Char(string='Card Title', default='Designed around your room')
    card_text = fields.Text(string='Card Text')

    badge_1_value = fields.Char(string='Badge 1 Value', default='50%')
    badge_1_label = fields.Char(string='Badge 1 Label', default='Build progress')
    badge_2_icon = fields.Char(string='Badge 2 Icon', default='fa-bell')
    badge_2_label = fields.Char(string='Badge 2 Label', default='Vendor updates')

    background_style = fields.Selection([
        ('charcoal', 'Charcoal Green'),
        ('sage', 'Sage Green'),
        ('olive', 'Olive'),
        ('warm', 'Warm Wood'),
    ], string='Background Style', default='charcoal')
