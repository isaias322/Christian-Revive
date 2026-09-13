from odoo import models, api


class ResPartnerGdpr(models.Model):
    _inherit = 'res.partner'

    @api.model
    def app_export_my_data(self, requester_partner_id):
        mode, scope = self._church_caller_scope(requester_partner_id=requester_partner_id)
        if mode != 'self':
            return {'success': False, 'error': 'Not authorized'}
        partner = self.sudo().browse(scope)

        pledges = self.env['church.give.pledge'].sudo().search([('member_id', '=', partner.id)])
        attendance = self.env['church.event.attendance'].sudo().search([('member_id', '=', partner.id)])
        donations = self.env['church.give.transaction'].sudo().search([('partner_id', '=', partner.id)])

        return {
            'success': True,
            'profile': {
                'name': partner.name, 'email': partner.email, 'phone': partner.phone,
                'date_of_birth': partner.date_of_birth.isoformat() if partner.date_of_birth else '',
                'membership_status': partner.membership_status,
                'member_join_date': partner.member_join_date.isoformat() if partner.member_join_date else '',
            },
            'pledges': [{
                'amount': p.pledge_amount, 'currency': p.currency, 'status': p.status,
            } for p in pledges],
            'attendance': [{
                'event': a.event_id.name if a.event_id else '',
                'checked_in_at': a.check_in_time.isoformat() if a.check_in_time else '',
            } for a in attendance],
            'donations': [{
                'amount': d.amount, 'currency': d.currency,
                'date': d.transaction_date.isoformat() if d.transaction_date else '',
            } for d in donations],
        }

    @api.model
    def app_request_account_deletion(self, requester_partner_id):
        mode, scope = self._church_caller_scope(requester_partner_id=requester_partner_id)
        if mode != 'self':
            return {'success': False, 'error': 'Not authorized'}
        partner = self.sudo().browse(scope)

        # Anonymize PII on this partner record; church.give.transaction rows
        # are never deleted or altered here, so financial totals/reporting
        # stay intact — only the donor's identifying fields are scrubbed.
        partner.write({
            'name': f'Deleted Member #{partner.id}',
            'email': False, 'phone': False, 'mobile': False, 'street': False,
            'city': False, 'date_of_birth': False, 'cnic': False,
            'app_login_email': False, 'app_password_hash': False,
            'is_app_profile': False, 'membership_status': 'inactive',
        })
        return {'success': True}
