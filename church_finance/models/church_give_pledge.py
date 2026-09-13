from odoo import models, fields, api


class ChurchGivePledge(models.Model):
    _name = 'church.give.pledge'
    _description = 'Giving Pledge'
    _order = 'start_date desc'

    member_id = fields.Many2one(
        'res.partner', string='Member', required=True,
        domain=[('is_member', '=', True)],
    )
    category_id = fields.Many2one('church.give.category', string='Category')
    project_id = fields.Many2one('church.give.project', string='Project')
    fund_id = fields.Many2one('church.give.fund', string='Fund')

    pledge_amount = fields.Float(string='Pledge Amount', required=True, digits=(16, 2))
    currency = fields.Selection([
        ('PKR', 'PKR'), ('USD', 'USD'), ('GBP', 'GBP'), ('EUR', 'EUR'),
    ], string='Currency', default='PKR', required=True)

    frequency = fields.Selection([
        ('one_time', 'One-time'), ('weekly', 'Weekly'), ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'), ('annual', 'Annual'),
    ], string='Frequency', default='one_time', required=True)

    start_date = fields.Date(string='Start Date', default=fields.Date.context_today, required=True)
    end_date = fields.Date(string='End Date')
    next_reminder_date = fields.Date(string='Next Reminder Date')

    status = fields.Selection([
        ('active', 'Active'), ('completed', 'Completed'),
        ('cancelled', 'Cancelled'), ('overdue', 'Overdue'),
    ], string='Status', default='active', required=True)

    notes = fields.Text(string='Notes')

    paid_amount = fields.Float(string='Paid So Far', compute='_compute_paid_amount', digits=(16, 2))
    progress_percent = fields.Float(string='Progress %', compute='_compute_paid_amount')

    def _compute_paid_amount(self):
        Transaction = self.env['church.give.transaction']
        for pledge in self:
            txs = Transaction.sudo().search([
                ('pledge_id', '=', pledge.id), ('state', '=', 'completed'),
            ])
            paid = sum(txs.mapped('amount'))
            pledge.paid_amount = paid
            pledge.progress_percent = (
                min(100.0, (paid / pledge.pledge_amount) * 100.0)
                if pledge.pledge_amount else 0.0
            )

    # ── Church Management RPC (Phase 3) ─────────────────────────

    @api.model
    def app_get_my_pledges(self, requester_partner_id):
        mode, scope = self.env['res.partner']._church_caller_scope(requester_partner_id=requester_partner_id)
        if mode != 'self':
            return {'success': False, 'error': 'Not authorized'}
        pledges = self.sudo().search([('member_id', '=', scope)], order='start_date desc')
        return {'success': True, 'pledges': self._read_pledges(pledges)}

    @api.model
    def app_create_pledge(self, vals, requester_partner_id=None, requester_staff_id=None):
        mode, scope = self.env['res.partner']._church_caller_scope(requester_partner_id, requester_staff_id)
        if mode == 'denied':
            return {'success': False, 'error': 'Not authorized'}

        vals = dict(vals or {})
        if mode == 'self':
            # A member may only pledge for themself.
            vals['member_id'] = scope
        elif 'member_id' not in vals:
            return {'success': False, 'error': 'member_id is required'}

        pledge = self.sudo().create(vals)
        return {'success': True, 'pledge_id': pledge.id}

    @api.model
    def app_get_pledges(self, requester_staff_id, status=None):
        employee = self.env['hr.employee'].sudo().browse(requester_staff_id)
        if not employee.exists() or employee.staff_role not in ('admin', 'finance_officer', 'pastor'):
            return {'success': False, 'error': 'Not authorized'}
        domain = [('status', '=', status)] if status else []
        pledges = self.sudo().search(domain, order='start_date desc')
        return {'success': True, 'pledges': self._read_pledges(pledges)}

    def _read_pledges(self, pledges):
        return [{
            'id': p.id, 'member_id': p.member_id.id, 'member_name': p.member_id.name,
            'pledge_amount': p.pledge_amount, 'currency': p.currency,
            'frequency': p.frequency,
            'start_date': p.start_date.isoformat() if p.start_date else '',
            'end_date': p.end_date.isoformat() if p.end_date else '',
            'status': p.status, 'paid_amount': p.paid_amount,
            'progress_percent': round(p.progress_percent, 1),
            'fund_id': p.fund_id.id if p.fund_id else False,
            'fund_name': p.fund_id.name if p.fund_id else '',
        } for p in pledges]
