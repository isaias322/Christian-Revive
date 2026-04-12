# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging
from datetime import date

_logger = logging.getLogger(__name__)


class ChurchGiveTransaction(models.Model):
    _name        = 'church.give.transaction'
    _description = 'Church Donation Transaction'
    _order       = 'create_date desc'
    _rec_name    = 'reference'
    _inherit     = ['mail.thread', 'mail.activity.mixin']

    reference = fields.Char(
        string='Reference', required=True, readonly=True,
        default=lambda self: self._generate_ref(),
        copy=False, tracking=True)

    app_transaction_id = fields.Char(
        string='App Transaction ID', index=True)

    partner_id = fields.Many2one(
        'res.partner', string='Donor', index=True, tracking=True)
    donor_name = fields.Char(
        string='Donor Name', compute='_compute_donor_name',
        store=True, readonly=False)
    donor_email = fields.Char(string='Donor Email')
    donor_phone = fields.Char(string='Donor Phone')
    app_user_id = fields.Char(string='App User ID', index=True)

    amount = fields.Float(
        string='Amount', required=True, digits=(16, 2), tracking=True)
    currency = fields.Selection([
        ('PKR', 'PKR — Pakistani Rupee'),
        ('USD', 'USD — US Dollar'),
        ('GBP', 'GBP — British Pound'),
        ('EUR', 'EUR — Euro'),
    ], string='Currency', required=True, default='PKR', tracking=True)
    amount_pkr = fields.Float(
        string='Amount (PKR equiv.)', compute='_compute_amount_pkr',
        store=True, digits=(16, 0))

    category_id = fields.Many2one(
        'church.give.category', string='Category',
        required=True, tracking=True)

    project_id = fields.Many2one(
        'church.give.project', string='Project', tracking=True,
        help='Leave empty for general giving.')
    project_name = fields.Char(
        related='project_id.name', string='Project Name', store=True)

    gateway = fields.Selection([
        ('easypaisa', 'EasyPaisa'),
        ('jazzcash',  'JazzCash'),
        ('stripe',    'Stripe (Card)'),
        ('paypal',    'PayPal'),
        ('cash',      'Cash / In-person'),
        ('bank',      'Bank Transfer'),
        ('other',     'Other'),
    ], string='Payment Gateway', required=True, default='cash', tracking=True)

    state = fields.Selection([
        ('pending',   'Pending'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ], string='Status', default='pending', required=True,
       tracking=True, index=True)

    gateway_reference = fields.Char(string='Gateway Reference', tracking=True)
    gateway_response  = fields.Text(string='Gateway Raw Response')

    note          = fields.Text(string='Donor Note')
    internal_note = fields.Text(string='Internal Note')
    transaction_date = fields.Datetime(
        string='Transaction Date', default=fields.Datetime.now,
        required=True, tracking=True)
    confirmed_by = fields.Many2one(
        'res.users', string='Confirmed By', readonly=True, tracking=True)
    confirmed_at  = fields.Datetime(string='Confirmed At', readonly=True)
    is_anonymous  = fields.Boolean(string='Anonymous', default=False)
    receipt_sent  = fields.Boolean(string='Receipt Sent', default=False)

    display_amount = fields.Char(
        string='Display Amount', compute='_compute_display_amount')

    # ── Compute ────────────────────────────────────────────────

    @api.depends('partner_id', 'donor_name')
    def _compute_donor_name(self):
        for rec in self:
            if rec.partner_id:
                rec.donor_name = rec.partner_id.name
            elif not rec.donor_name:
                rec.donor_name = 'Anonymous'

    @api.depends('amount', 'currency')
    def _compute_amount_pkr(self):
        rates = {'PKR': 1.0, 'USD': 285.0, 'GBP': 360.0, 'EUR': 308.0}
        for rec in self:
            rec.amount_pkr = rec.amount * rates.get(rec.currency, 1.0)

    @api.depends('amount', 'currency')
    def _compute_display_amount(self):
        symbols = {'PKR': 'Rs', 'USD': '$', 'GBP': '£', 'EUR': '€'}
        for rec in self:
            sym = symbols.get(rec.currency, rec.currency)
            if rec.currency == 'PKR':
                rec.display_amount = f'{sym} {rec.amount:,.0f}'
            else:
                rec.display_amount = f'{sym} {rec.amount:,.2f}'

    # ── Actions ────────────────────────────────────────────────

    def action_confirm(self):
        for rec in self:
            if rec.state != 'pending':
                raise UserError('Only pending transactions can be confirmed.')
            rec.write({
                'state':        'completed',
                'confirmed_by': self.env.uid,
                'confirmed_at': fields.Datetime.now(),
            })
            rec.message_post(
                body=f'Transaction confirmed by {self.env.user.name}',
                message_type='comment')
        return True

    def action_fail(self):
        for rec in self:
            rec.write({'state': 'failed'})
            rec.message_post(body='Transaction marked as failed.',
                             message_type='comment')

    def action_refund(self):
        for rec in self:
            if rec.state != 'completed':
                raise UserError('Only completed transactions can be refunded.')
            rec.write({'state': 'refunded'})
            rec.message_post(body='Transaction refunded.',
                             message_type='comment')

    def action_send_receipt(self):
        for rec in self:
            email = rec.donor_email or (
                rec.partner_id.email if rec.partner_id else None)
            if not email:
                raise UserError('No email address found for this donor.')
            rec.receipt_sent = True
            rec.message_post(body=f'Receipt sent to {email}',
                             message_type='comment')
        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'title':   'Receipt Sent',
                'message': 'Donation receipt has been emailed to the donor.',
                'type':    'success',
            },
        }

    # ── Helpers ────────────────────────────────────────────────

    @api.model
    def _generate_ref(self):
        today = date.today()
        seq   = self.search_count([]) + 1
        return f'GIV-{today.year}{today.month:02d}{today.day:02d}-{seq:04d}'

    # ── App API ────────────────────────────────────────────────

    @api.model
    def app_record_transaction(self, *args, **kwargs):
        args = [a for a in args if a != []]
        data = kwargs if kwargs else (args[0] if args else {})

        # Category
        category_code = data.get('category_code', 'offering')
        category = self.env['church.give.category'].search(
            [('code', '=', category_code)], limit=1)
        if not category:
            category = self.env['church.give.category'].search([], limit=1)
        if not category:
            raise ValidationError(
                f'Give category "{category_code}" not found.')

        # Project
        project_id  = False
        project_code = data.get('project_code', '')
        if project_code:
            project = self.env['church.give.project'].search(
                [('code', '=', project_code)], limit=1)
            if project:
                project_id = project.id

        # Partner
        partner     = None
        donor_email = data.get('donor_email', '')
        donor_name  = data.get('donor_name', '')
        if donor_email:
            partner = self.env['res.partner'].search(
                [('email', '=', donor_email)], limit=1)
        if not partner and donor_name and donor_name != 'App User':
            partner = self.env['res.partner'].search(
                [('name', 'ilike', donor_name)], limit=1)

        # Duplicate check
        existing = self.search([
            ('app_transaction_id', '=', data.get('app_transaction_id', ''))
        ], limit=1)
        if existing:
            existing.write({
                'state':             data.get('state', existing.state),
                'gateway_reference': data.get('gateway_reference',
                                              existing.gateway_reference),
            })
            return {
                'success':   True,
                'odoo_id':   existing.id,
                'reference': existing.reference,
                'message':   'Transaction updated',
            }

        vals = {
            'app_transaction_id': data.get('app_transaction_id', ''),
            'app_user_id':        data.get('app_user_id', ''),
            'partner_id':         partner.id if partner else False,
            'donor_name':         donor_name or 'App User',
            'donor_email':        donor_email or (partner.email if partner else ''),
            'donor_phone':        data.get('donor_phone', '') or (
                                      (partner.phone or partner.mobile)
                                      if partner else ''),
            'amount':             float(data.get('amount', 0)),
            'currency':           data.get('currency', 'PKR'),
            'category_id':        category.id,
            'project_id':         project_id,
            'gateway':            data.get('gateway', 'cash'),
            'state':              data.get('state', 'pending'),
            'gateway_reference':  data.get('gateway_reference', ''),
            'note':               data.get('note', ''),
            'transaction_date':   fields.Datetime.now(),
        }

        tx = self.create(vals)
        _logger.info('App transaction: %s | %s %s | %s',
                     tx.reference, vals['currency'],
                     vals['amount'], vals['gateway'])

        return {
            'success':   True,
            'odoo_id':   tx.id,
            'reference': tx.reference,
            'message':   'Transaction recorded successfully',
        }

    @api.model
    def app_get_transactions(self, *args, **kwargs):
        args = [a for a in args if a != []]
        data = kwargs if kwargs else (args[0] if args else {})

        app_user_id = data.get('app_user_id', '')
        limit       = int(data.get('limit', 50))
        offset      = int(data.get('offset', 0))

        domain = []
        if app_user_id:
            domain.append(('app_user_id', '=', app_user_id))

        txs = self.search(domain, limit=limit, offset=offset,
                          order='transaction_date desc')
        return [{
            'id':                 tx.id,
            'odoo_id':            tx.id,
            'app_transaction_id': tx.app_transaction_id or '',
            'reference':          tx.reference,
            'donor_name':         tx.donor_name or '',
            'amount':             tx.amount,
            'currency':           tx.currency,
            'display_amount':     tx.display_amount,
            'category':           tx.category_id.code if tx.category_id else '',
            'category_label':     tx.category_id.name if tx.category_id else '',
            'gateway':            tx.gateway,
            'state':              tx.state,
            'gateway_reference':  tx.gateway_reference or '',
            'note':               tx.note or '',
            'project_code':       tx.project_id.code if tx.project_id else '',
            'project_name':       tx.project_id.name if tx.project_id else '',
            'transaction_date':   tx.transaction_date.isoformat() if tx.transaction_date else '',
            'created_at':         tx.create_date.isoformat() if tx.create_date else '',
        } for tx in txs]

    @api.model
    def app_get_totals(self, *args, **kwargs):
        args = [a for a in args if a != []]
        data = kwargs if kwargs else (args[0] if args else {})

        app_user_id = data.get('app_user_id', '')
        domain = [('state', '=', 'completed')]
        if app_user_id:
            domain.append(('app_user_id', '=', app_user_id))

        txs    = self.search(domain)
        totals = {}
        for tx in txs:
            key = tx.category_id.name if tx.category_id else 'Other'
            if key not in totals:
                totals[key] = {'pkr': 0.0, 'usd': 0.0, 'total_pkr': 0.0}
            if tx.currency == 'PKR':
                totals[key]['pkr'] += tx.amount
            elif tx.currency == 'USD':
                totals[key]['usd'] += tx.amount
            totals[key]['total_pkr'] += tx.amount_pkr
        return totals

    @api.model
    def app_confirm_transaction(self, *args, **kwargs):
        args = [a for a in args if a != []]
        data = kwargs if kwargs else (args[0] if args else {})

        tx = self.search([
            ('app_transaction_id', '=', data.get('app_transaction_id', ''))
        ], limit=1)
        if not tx:
            return {'success': False, 'message': 'Transaction not found'}

        tx.write({
            'state':             'completed',
            'gateway_reference': data.get('gateway_reference',
                                          tx.gateway_reference),
            'confirmed_at':      fields.Datetime.now(),
        })
        return {
            'success':   True,
            'reference': tx.reference,
            'message':   'Transaction confirmed',
        }

    @api.model
    def app_get_projects(self, *args, **kwargs):
        args     = [a for a in args if a != []]
        projects = self.env['church.give.project'].search(
            [('is_active', '=', True)], order='sequence asc')
        return [{
            'id':                p.id,
            'name':              p.name,
            'code':              p.code,
            'icon':              p.icon,
            'description':       p.description or '',
            'goal_amount':       p.goal_amount,
            'raised_amount':     p.raised_amount,
            'progress_percent':  p.progress_percent,
            'transaction_count': p.transaction_count,
        } for p in projects]