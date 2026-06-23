# -*- coding: utf-8 -*-
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def write(self, vals):
        previous_states = {picking.id: picking.state for picking in self}
        res = super().write(vals)
        if 'state' in vals:
            for picking in self:
                order = picking.sale_id
                if not order or picking.picking_type_id.code != 'outgoing':
                    continue
                if previous_states.get(picking.id) == picking.state:
                    continue
                if picking.state == 'assigned' and order.delivery_stage in ('processing',):
                    order._lifestyle_advance_stage('packing')
                elif picking.state == 'done':
                    if order.fulfillment_type == 'pickup':
                        order._lifestyle_advance_stage('ready_for_pickup')
                    else:
                        order._lifestyle_advance_stage('out_for_delivery')
        return res
