# -*- coding: utf-8 -*-
from odoo import fields, models


class IrAttachment(models.Model):
    """Stamps each vendor-sent order photo/video with the order's delivery
    stage at the moment it was sent, so the customer app can still show e.g.
    "Build & Packing" on that specific photo even after the order has since
    moved on to a later stage."""
    _inherit = 'ir.attachment'

    lifestyle_stage_label = fields.Char(string='Order Stage At Send Time', copy=False)
