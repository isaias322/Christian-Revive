from collections import defaultdict
from odoo import models, api


class ChurchReport(models.TransientModel):
    _name = 'church.report'
    _description = 'Church Management Reports'

    def _staff_role(self, requester_staff_id):
        if not requester_staff_id:
            return None
        employee = self.env['hr.employee'].sudo().browse(requester_staff_id)
        if not employee.exists():
            return None
        return employee.staff_role

    @api.model
    def app_get_membership_growth(self, requester_staff_id=None):
        role = self._staff_role(requester_staff_id)
        if role not in ('admin', 'pastor'):
            return {'success': False, 'error': 'Not authorized'}

        ResPartner = self.env['res.partner']
        joined = ResPartner.sudo().search([
            ('is_member', '=', True), ('member_join_date', '!=', False),
        ])
        by_month = defaultdict(int)
        for m in joined:
            by_month[m.member_join_date.strftime('%Y-%m')] += 1

        by_status = defaultdict(int)
        for m in ResPartner.sudo().search([('is_member', '=', True)]):
            by_status[m.membership_status or 'visitor'] += 1

        return {
            'success': True,
            'by_month': [{'month': k, 'new_members': v} for k, v in sorted(by_month.items())],
            'by_status': [{'status': k, 'count': v} for k, v in by_status.items()],
        }

    @api.model
    def app_get_giving_by_fund(self, requester_staff_id=None):
        role = self._staff_role(requester_staff_id)
        if role not in ('admin', 'finance_officer'):
            return {'success': False, 'error': 'Not authorized'}

        transactions = self.env['church.give.transaction'].sudo().search([
            ('state', '=', 'completed'),
        ])
        by_fund = defaultdict(float)
        by_category = defaultdict(float)
        for tx in transactions:
            by_fund[tx.fund_id.name if tx.fund_id else 'Unrestricted'] += tx.amount_pkr
            by_category[tx.category_id.name if tx.category_id else 'Uncategorized'] += tx.amount_pkr

        return {
            'success': True,
            'by_fund': [{'fund': k, 'total_pkr': v} for k, v in by_fund.items()],
            'by_category': [{'category': k, 'total_pkr': v} for k, v in by_category.items()],
        }

    @api.model
    def app_get_attendance_trends(self, requester_staff_id=None):
        role = self._staff_role(requester_staff_id)
        if role not in ('admin', 'pastor'):
            return {'success': False, 'error': 'Not authorized'}

        records = self.env['church.event.attendance'].sudo().search([])
        by_event = defaultdict(int)
        for rec in records:
            by_event[rec.event_id.name if rec.event_id else 'Unknown Event'] += 1

        return {
            'success': True,
            'by_event': [{'event': k, 'attendance_count': v} for k, v in by_event.items()],
        }
