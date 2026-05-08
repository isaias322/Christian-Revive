from odoo import fields, models, api
from werkzeug.security import generate_password_hash, check_password_hash

class ResPartnerProfile(models.Model):
    _inherit = 'res.partner'

    is_app_profile = fields.Boolean(string='App Profile', default=False)
    app_password_hash = fields.Char(string='App Password (Hash)')
    app_login_email = fields.Char(string='App Login Email')

    donation_transaction_ids = fields.One2many(
        'donation.transaction', 'partner_id', string='Donations')

    total_donated = fields.Float(
        string='Total Donated', compute='_compute_total_donated', store=True)

    donation_transaction_count = fields.Integer(
        string='Donation Count', compute='_compute_total_donated', store=True)

    @api.depends('donation_transaction_ids', 'donation_transaction_ids.amount', 'donation_transaction_ids.status')
    def _compute_total_donated(self):
        for partner in self:
            confirmed = partner.donation_transaction_ids.filtered(lambda t: t.status == 'confirmed')
            partner.total_donated = sum(confirmed.mapped('amount'))
            partner.donation_transaction_count = len(confirmed)

    @api.model
    def app_register(self, email, password, vals):
        """Register a new app user"""
        if not email or not password:
            return {'success': False, 'error': 'Email and password are required'}
        existing = self.sudo().search([
            ('app_login_email', '=', email.strip().lower()),
            ('is_app_profile', '=', True),
        ], limit=1)
        if existing:
            return {'success': False, 'error': 'Email already registered'}

        vals.update({
            'is_app_profile': True,
            'app_login_email': email.strip().lower(),
            'app_password_hash': generate_password_hash(password),
        })
        partner = self.sudo().create(vals)
        return {'success': True, 'partner_id': partner.id}

    @api.model
    def app_login(self, email, password):
        """Login an app user"""
        if not email or not password:
            return {'success': False, 'error': 'Invalid email or password'}
        partner = self.sudo().search([
            ('app_login_email', '=', email.strip().lower()),
            ('is_app_profile', '=', True),
        ], limit=1)
        if partner and check_password_hash(partner.app_password_hash, password):
            return {'success': True, 'partner_id': partner.id}
        return {'success': False, 'error': 'Invalid email or password'}