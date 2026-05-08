from odoo.tests.common import TransactionCase


class TestChurchGiveTransaction(TransactionCase):

    def _create_tx(self, amount=100.0, currency='PKR', **kwargs):
        return self.env['church.give.transaction'].sudo().create({
            'amount': amount,
            'currency': currency,
            **kwargs,
        })

    # ── Reference generation ─────────────────────────────────────────────────

    def test_unique_references(self):
        tx1 = self._create_tx()
        tx2 = self._create_tx()
        self.assertNotEqual(
            tx1.name, tx2.name,
            'Each transaction must get a unique reference',
        )

    def test_reference_not_empty(self):
        tx = self._create_tx()
        self.assertTrue(tx.name, 'Reference must not be empty')

    # ── Exchange-rate conversion ─────────────────────────────────────────────

    def test_pkr_conversion_is_identity(self):
        tx = self._create_tx(amount=1000.0, currency='PKR')
        self.assertAlmostEqual(tx.amount_pkr, 1000.0, places=2)

    def test_usd_uses_config_rate(self):
        rate = float(
            self.env['ir.config_parameter'].sudo().get_param(
                'give.exchange_rate.usd', '285.0'
            )
        )
        tx = self._create_tx(amount=1.0, currency='USD')
        self.assertAlmostEqual(tx.amount_pkr, rate, places=2)

    def test_gbp_uses_config_rate(self):
        rate = float(
            self.env['ir.config_parameter'].sudo().get_param(
                'give.exchange_rate.gbp', '360.0'
            )
        )
        tx = self._create_tx(amount=1.0, currency='GBP')
        self.assertAlmostEqual(tx.amount_pkr, rate, places=2)

    def test_eur_uses_config_rate(self):
        rate = float(
            self.env['ir.config_parameter'].sudo().get_param(
                'give.exchange_rate.eur', '308.0'
            )
        )
        tx = self._create_tx(amount=1.0, currency='EUR')
        self.assertAlmostEqual(tx.amount_pkr, rate, places=2)

    def test_rate_change_reflected(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'give.exchange_rate.usd', '300.0'
        )
        tx = self._create_tx(amount=2.0, currency='USD')
        self.assertAlmostEqual(tx.amount_pkr, 600.0, places=2)
        # restore
        self.env['ir.config_parameter'].sudo().set_param(
            'give.exchange_rate.usd', '285.0'
        )
