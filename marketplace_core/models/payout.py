# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MarketplaceWalletTransaction(models.Model):
    _name = 'marketplace.wallet.transaction'
    _description = 'Seller Wallet Transaction'
    _order = 'create_date desc'

    seller_id = fields.Many2one(
        'marketplace.seller', required=True, index=True, ondelete='cascade')
    order_id = fields.Many2one('sale.order', ondelete='set null')
    payout_id = fields.Many2one(
        'marketplace.seller.payout', ondelete='set null')
    transaction_type = fields.Selection([
        ('sale_credit', 'Sale Credit'),
        ('payout_debit', 'Payout'),
        ('refund_debit', 'Refund Deduction'),
        ('adjustment', 'Manual Adjustment'),
    ], required=True)
    amount = fields.Monetary(
        required=True, help='Always positive; direction from the type.')
    signed_amount = fields.Monetary(
        compute='_compute_signed_amount', store=True)
    currency_id = fields.Many2one(
        related='seller_id.currency_id', store=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], default='done', required=True)
    note = fields.Char()

    @api.depends('amount', 'transaction_type')
    def _compute_signed_amount(self):
        for tx in self:
            sign = 1 if tx.transaction_type in (
                'sale_credit', 'adjustment') else -1
            # adjustments may be entered negative on purpose
            tx.signed_amount = sign * tx.amount if tx.transaction_type != \
                'adjustment' else tx.amount


class MarketplaceSellerPayout(models.Model):
    _name = 'marketplace.seller.payout'
    _description = 'Seller Payout Request'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(
        required=True, copy=False, readonly=True, default=lambda s: _('New'))
    seller_id = fields.Many2one(
        'marketplace.seller', required=True, index=True, ondelete='restrict')
    amount = fields.Monetary(required=True, tracking=True)
    currency_id = fields.Many2one(
        related='seller_id.currency_id', store=True)
    payout_method = fields.Selection(
        related='seller_id.payout_method', store=True, readonly=True)
    state = fields.Selection([
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ], default='requested', required=True, tracking=True, index=True)
    payment_reference = fields.Char(
        help='Bank / wallet transaction reference once paid.')
    paid_date = fields.Datetime()
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                    'marketplace.seller.payout') or _('New')
        return super().create(vals_list)

    @api.model
    def request_payout(self, seller, amount):
        amount = float(amount)
        if amount <= 0:
            raise UserError(_('Payout amount must be positive.'))
        if seller.kyc_status != 'verified':
            raise UserError(_(
                'KYC verification is required before your first payout. '
                'Please complete KYC in your shop settings.'))
        pending = sum(self.sudo().search([
            ('seller_id', '=', seller.id),
            ('state', 'in', ('requested', 'approved'))]).mapped('amount'))
        if amount > seller.wallet_balance - pending:
            raise UserError(_(
                'Requested amount exceeds your available balance '
                '(%(balance).2f, of which %(pending).2f already requested).',
                balance=seller.wallet_balance, pending=pending))
        if not seller.payout_method:
            raise UserError(_('Set up a payout method first.'))
        return self.sudo().create({
            'seller_id': seller.id,
            'amount': amount,
        })

    def action_approve(self):
        self.filtered(lambda p: p.state == 'requested').write(
            {'state': 'approved'})

    def action_mark_paid(self):
        for payout in self:
            if payout.state not in ('requested', 'approved'):
                raise UserError(_('Only pending payouts can be paid.'))
            payout.write({
                'state': 'paid',
                'paid_date': fields.Datetime.now(),
            })
            self.env['marketplace.wallet.transaction'].sudo().create({
                'seller_id': payout.seller_id.id,
                'payout_id': payout.id,
                'transaction_type': 'payout_debit',
                'amount': payout.amount,
                'state': 'done',
                'note': _('Payout %s') % payout.name,
            })

    def action_reject(self):
        self.filtered(
            lambda p: p.state in ('requested', 'approved')
        ).write({'state': 'rejected'})
