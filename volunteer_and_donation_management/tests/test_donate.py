from odoo.tests.common import TransactionCase


class TestDonation(TransactionCase):

    def _make_donation(self, amount, **kwargs):
        return self.env['donate.record'].sudo().app_create_donation(
            amount=amount,
            **kwargs,
        )

    # ── Amount validation ────────────────────────────────────────────────────

    def test_zero_amount_rejected(self):
        result = self._make_donation(0)
        self.assertEqual(result.get('status'), 'error')

    def test_negative_amount_rejected(self):
        result = self._make_donation(-50)
        self.assertEqual(result.get('status'), 'error')

    def test_none_amount_rejected(self):
        result = self._make_donation(None)
        self.assertEqual(result.get('status'), 'error')

    def test_valid_amount_accepted(self):
        result = self._make_donation(100)
        self.assertEqual(result.get('status'), 'success')

    def test_float_amount_accepted(self):
        result = self._make_donation(0.01)
        self.assertEqual(result.get('status'), 'success')

    def test_string_numeric_amount_accepted(self):
        result = self._make_donation('500')
        self.assertEqual(result.get('status'), 'success')
