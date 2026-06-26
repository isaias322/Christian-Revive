# -*- coding: utf-8 -*-
from odoo import models, fields


class LifestyleAppBanner(models.Model):
    _name = 'lifestyle.app.banner'
    _description = 'Revive Lifestyle App News Banner'
    _order = 'sequence, id'

    name = fields.Char(string='Internal Name', required=True)
    title = fields.Char(string='Title', required=True)
    subtitle = fields.Text(string='Description')
    image = fields.Binary(string='Banner Image')
    background_style = fields.Selection([
        ('charcoal', 'Charcoal'),
        ('sage', 'Sage Green'),
        ('sage_light', 'Light Sage'),
        ('terracotta', 'Terracotta'),
        ('cream', 'Cream'),
        ('custom', 'Custom Color'),
    ], string='Background Style', default='charcoal')
    background_color = fields.Char(
        string='Custom Background Color',
        help='Use a hex color like #2E2E2A. Only used when Background Style is Custom Color.',
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
