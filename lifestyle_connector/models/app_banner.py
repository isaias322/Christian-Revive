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
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
