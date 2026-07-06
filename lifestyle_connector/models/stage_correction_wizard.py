# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError

from .sale_order import STAGE_LABELS, DELIVERY_STAGE_SEQUENCE, PICKUP_STAGE_SEQUENCE


class LifestyleStageCorrectionWizard(models.TransientModel):
    """Backend stage correction: pick any stage of the order's flow.

    Corrections are silent by default - the customer is only notified when
    the checkbox is ticked, or later via the order's "Send Status Email"
    button. The wizard also keeps the old app flow available: "Unlock for
    Vendor App" arms a one-time correction from the vendor's phone.
    """
    _name = 'lifestyle.stage.correction.wizard'
    _description = 'Correct Delivery Stage'

    order_id = fields.Many2one('sale.order', string='Order', required=True, readonly=True)
    current_stage = fields.Selection(
        list(STAGE_LABELS.items()), string='Current Stage',
        related='order_id.delivery_stage',
    )
    new_stage = fields.Selection(
        list(STAGE_LABELS.items()), string='Set Stage To', required=True,
    )
    notify_customer = fields.Boolean(
        string='Notify Customer',
        default=False,
        help='Send the app push / email about this stage. Leave off for a '
             'silent correction; you can always notify later with the '
             '"Send Status Email" button on the order.',
    )

    def _order_sequence(self):
        self.ensure_one()
        order = self.order_id
        sequence = PICKUP_STAGE_SEQUENCE if order.fulfillment_type == 'pickup' else DELIVERY_STAGE_SEQUENCE
        if order._lifestyle_skip_processing():
            sequence = [stage for stage in sequence if stage != 'processing']
        return sequence

    def action_apply(self):
        self.ensure_one()
        order = self.order_id
        sequence = self._order_sequence()
        if self.new_stage not in sequence:
            allowed = ', '.join(STAGE_LABELS[stage] for stage in sequence)
            raise UserError(
                'Stage "%s" is not part of this order\'s flow.\n\nAllowed stages: %s'
                % (STAGE_LABELS.get(self.new_stage, self.new_stage), allowed)
            )
        if self.new_stage == order.delivery_stage:
            return {'type': 'ir.actions.act_window_close'}
        # Moving backward normally needs the one-time unlock; opening this
        # wizard IS the staff's explicit permission, so arm it here.
        if (order.delivery_stage in sequence
                and sequence.index(self.new_stage) < sequence.index(order.delivery_stage)
                and not order.lifestyle_stage_unlocked):
            order.lifestyle_stage_unlocked = True
        order._lifestyle_advance_stage(self.new_stage, push=self.notify_customer)
        return {'type': 'ir.actions.act_window_close'}

    def action_unlock_app(self):
        """Old behavior: just arm a one-time correction from the vendor app."""
        self.ensure_one()
        self.order_id.action_unlock_stage_correction()
        return {'type': 'ir.actions.act_window_close'}
