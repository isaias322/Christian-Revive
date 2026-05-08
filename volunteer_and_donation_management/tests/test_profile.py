from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from werkzeug.security import check_password_hash


class TestAppProfile(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Profile = self.env['res.partner']
        self.model = self.env['volunteer.profile']

    # ── Registration ────────────────────────────────────────────────────────

    def test_register_stores_hashed_password(self):
        result = self.env['res.partner'].sudo().app_register(
            name='Test User',
            email='test_hash@example.com',
            password='SecurePass123',
        )
        self.assertEqual(result.get('status'), 'success')
        partner = self.env['res.partner'].sudo().search(
            [('email', '=', 'test_hash@example.com')], limit=1
        )
        self.assertTrue(partner, 'Partner should be created')
        self.assertTrue(
            partner.app_password_hash,
            'Password hash should be stored',
        )
        self.assertNotEqual(
            partner.app_password_hash, 'SecurePass123',
            'Raw password must not be stored',
        )
        self.assertTrue(
            check_password_hash(partner.app_password_hash, 'SecurePass123'),
            'Stored hash should verify against original password',
        )

    def test_register_duplicate_email_rejected(self):
        self.env['res.partner'].sudo().app_register(
            name='First User',
            email='dup@example.com',
            password='Pass1',
        )
        result = self.env['res.partner'].sudo().app_register(
            name='Second User',
            email='dup@example.com',
            password='Pass2',
        )
        self.assertEqual(result.get('status'), 'error')

    def test_register_missing_fields_rejected(self):
        result = self.env['res.partner'].sudo().app_register(
            name='',
            email='',
            password='',
        )
        self.assertEqual(result.get('status'), 'error')

    # ── Login ────────────────────────────────────────────────────────────────

    def test_login_correct_password_succeeds(self):
        self.env['res.partner'].sudo().app_register(
            name='Login User',
            email='login_ok@example.com',
            password='Correct123',
        )
        result = self.env['res.partner'].sudo().app_login(
            email='login_ok@example.com',
            password='Correct123',
        )
        self.assertEqual(result.get('status'), 'success')

    def test_login_wrong_password_fails(self):
        self.env['res.partner'].sudo().app_register(
            name='Login User 2',
            email='login_bad@example.com',
            password='RightPass',
        )
        result = self.env['res.partner'].sudo().app_login(
            email='login_bad@example.com',
            password='WrongPass',
        )
        self.assertEqual(result.get('status'), 'error')

    def test_login_nonexistent_email_fails(self):
        result = self.env['res.partner'].sudo().app_login(
            email='nobody@example.com',
            password='irrelevant',
        )
        self.assertEqual(result.get('status'), 'error')

    def test_login_email_normalised(self):
        self.env['res.partner'].sudo().app_register(
            name='Case User',
            email='Case@Example.COM',
            password='Pass123',
        )
        result = self.env['res.partner'].sudo().app_login(
            email='  case@example.com  ',
            password='Pass123',
        )
        self.assertEqual(result.get('status'), 'success')
