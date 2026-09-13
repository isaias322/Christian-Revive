from odoo import models, fields, api
from odoo.exceptions import UserError


class ChurchGiveReconciliationBatch(models.Model):
    _name = 'church.give.reconciliation.batch'
    _description = 'Giving Reconciliation Batch'
    _order = 'date desc'

    name = fields.Char(string='Batch Reference', required=True, readonly=True,
                        default=lambda self: self._generate_ref(), copy=False)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    transaction_ids = fields.Many2many('church.give.transaction', string='Transactions')
    total_amount = fields.Float(string='Total (PKR equiv.)', compute='_compute_total_amount', digits=(16, 0))
    status = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True)
    prepared_by_id = fields.Many2one('hr.employee', string='Prepared By')
    approved_by_id = fields.Many2one('hr.employee', string='Approved By', readonly=True)
    approved_at = fields.Datetime(string='Approved At', readonly=True)
    notes = fields.Text(string='Notes')

    @api.depends('transaction_ids', 'transaction_ids.amount_pkr')
    def _compute_total_amount(self):
        for batch in self:
            batch.total_amount = sum(batch.transaction_ids.mapped('amount_pkr'))

    @api.model
    def _generate_ref(self):
        return self.env['ir.sequence'].next_by_code('church.give.reconciliation.batch') or 'RECON-NEW'

    def action_submit(self):
        for batch in self:
            if batch.status != 'draft':
                raise UserError('Only draft batches can be submitted.')
            batch.status = 'submitted'

    def _approver_ok(self, requester_staff_id):
        if not requester_staff_id:
            return False
        employee = self.env['hr.employee'].sudo().browse(requester_staff_id)
        return employee.exists() and employee.staff_role in ('admin', 'finance_officer')

    # ── Church Management RPC (Phase 3) ─────────────────────────

    @api.model
    def app_get_reconciliation_batches(self, requester_staff_id):
        if not self._approver_ok(requester_staff_id):
            return {'success': False, 'error': 'Not authorized'}
        batches = self.sudo().search([], order='date desc')
        return {'success': True, 'batches': [{
            'id': b.id, 'name': b.name, 'date': b.date.isoformat() if b.date else '',
            'status': b.status, 'total_amount': b.total_amount,
            'transaction_count': len(b.transaction_ids),
        } for b in batches]}

    @api.model
    def app_create_reconciliation_batch(self, transaction_ids, requester_staff_id):
        if not self._approver_ok(requester_staff_id):
            return {'success': False, 'error': 'Not authorized'}
        employee = self.env['hr.employee'].sudo().browse(requester_staff_id)
        batch = self.sudo().create({
            'transaction_ids': [(6, 0, transaction_ids)],
            'prepared_by_id': employee.id,
        })
        return {'success': True, 'batch_id': batch.id}

    @api.model
    def app_approve_reconciliation_batch(self, batch_id, requester_staff_id):
        if not self._approver_ok(requester_staff_id):
            return {'success': False, 'error': 'Not authorized'}
        batch = self.sudo().browse(batch_id)
        if not batch.exists():
            return {'success': False, 'error': 'Batch not found'}
        if batch.status not in ('draft', 'submitted'):
            return {'success': False, 'error': 'Batch already finalized'}

        employee = self.env['hr.employee'].sudo().browse(requester_staff_id)
        batch.sudo().write({
            'status': 'approved',
            'approved_by_id': employee.id,
            'approved_at': fields.Datetime.now(),
        })
        batch.transaction_ids.filtered(lambda t: t.state == 'pending').write({
            'state': 'completed',
            'confirmed_by': employee.user_id.id if employee.user_id else False,
            'confirmed_at': fields.Datetime.now(),
        })
        return {'success': True}
