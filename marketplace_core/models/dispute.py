# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MarketplaceDispute(models.Model):
    _name = 'marketplace.dispute'
    _description = 'Marketplace Dispute'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        required=True, copy=False, readonly=True, default=lambda s: _('New'))
    order_id = fields.Many2one(
        'sale.order', required=True, ondelete='restrict', index=True,
        domain=[('is_marketplace_order', '=', True)])
    buyer_id = fields.Many2one(
        'res.partner', string='Buyer', related='order_id.partner_id',
        store=True)
    seller_id = fields.Many2one(
        related='order_id.marketplace_seller_id', store=True)
    reason = fields.Selection([
        ('not_received', 'Item not received'),
        ('not_as_described', 'Item not as described'),
        ('damaged', 'Item damaged'),
        ('counterfeit', 'Suspected counterfeit'),
        ('other', 'Other'),
    ], required=True, tracking=True)
    description = fields.Text(string='Buyer Statement')
    state = fields.Selection([
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved_refund', 'Resolved - Buyer Refunded'),
        ('resolved_release', 'Resolved - Released to Seller'),
        ('cancelled', 'Cancelled'),
    ], default='open', required=True, tracking=True, index=True)
    resolution_notes = fields.Text()
    currency_id = fields.Many2one(related='order_id.currency_id')
    amount = fields.Monetary(related='order_id.amount_total')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'marketplace.dispute') or _('New')
        disputes = super().create(vals_list)
        for dispute in disputes:
            dispute.order_id.message_post(body=_(
                'Dispute %(name)s opened: %(reason)s',
                name=dispute.name,
                reason=dict(dispute._fields['reason'].selection)[dispute.reason]))
        return disputes

    @api.model
    def open_for_order(self, order, partner, reason, description=None):
        if order.partner_id != partner:
            raise UserError(_('You can only dispute your own orders.'))
        if order.escrow_state != 'held':
            raise UserError(_(
                'A dispute can only be opened while funds are still held '
                'in escrow.'))
        existing = self.sudo().search([
            ('order_id', '=', order.id),
            ('state', 'in', ('open', 'under_review'))], limit=1)
        if existing:
            raise UserError(_('There is already an open dispute for this order.'))
        return self.sudo().create({
            'order_id': order.id,
            'reason': reason,
            'description': description or False,
        })

    def action_start_review(self):
        self.filtered(lambda d: d.state == 'open').write(
            {'state': 'under_review'})

    def action_resolve_refund(self):
        for dispute in self:
            if dispute.state not in ('open', 'under_review'):
                raise UserError(_('This dispute is already closed.'))
            dispute.state = 'resolved_refund'
            if dispute.order_id.escrow_state == 'held':
                dispute.order_id.action_refund_escrow()
            dispute.message_post(body=_(
                'Resolved in favour of the buyer: escrow refunded.'))

    def action_resolve_release(self):
        for dispute in self:
            if dispute.state not in ('open', 'under_review'):
                raise UserError(_('This dispute is already closed.'))
            dispute.state = 'resolved_release'
            if dispute.order_id.escrow_state == 'held':
                dispute.order_id.action_release_escrow()
            dispute.message_post(body=_(
                'Resolved in favour of the seller: escrow released.'))

    def action_cancel(self):
        self.filtered(
            lambda d: d.state in ('open', 'under_review')
        ).write({'state': 'cancelled'})
