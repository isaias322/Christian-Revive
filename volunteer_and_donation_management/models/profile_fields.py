import hashlib
from odoo import fields, models, api

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

    def app_register(self, email, password, vals):
        """Register a new app user"""
        # Check if email already exists
        existing = self.sudo().search([
            ('app_login_email', '=', email),
            ('is_app_profile', '=', True),
        ], limit=1)
        if existing:
            return {'success': False, 'error': 'Email already registered'}

        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        vals.update({
            'is_app_profile': True,
            'app_login_email': email,
            'app_password_hash': pw_hash,
        })
        partner = self.sudo().create(vals)
        return {'success': True, 'partner_id': partner.id}

    def app_login(self, email, password):
        """Login an app user"""
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        partner = self.sudo().search([
            ('app_login_email', '=', email),
            ('app_password_hash', '=', pw_hash),
            ('is_app_profile', '=', True),
        ], limit=1)
        if partner:
            return {'success': True, 'partner_id': partner.id}
        return {'success': False, 'error': 'Invalid email or password'}