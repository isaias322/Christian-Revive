# -*- coding: utf-8 -*-
from odoo import models, fields


class LifestyleRoomCategory(models.Model):
    _name = 'lifestyle.room.category'
    _description = 'Room Category'
    _order = 'sequence, name'

    name = fields.Char(string='Room Name', required=True)
    sequence = fields.Integer(default=10)
    product_ids = fields.Many2many(
        'product.template',
        'lifestyle_product_room_rel',
        'room_id',
        'product_id',
        string='Products',
    )
