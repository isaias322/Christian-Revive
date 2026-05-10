from odoo import models, fields


class OneVoicePrayerPledge(models.Model):
    _name = 'onevoice.prayer.pledge'
    _description = 'Prayer Wall Entry'

    pledge_name = fields.Char()
    pledge_text = fields.Text()
    pray_count  = fields.Integer()
    posted_date = fields.Datetime()
    source_key  = fields.Char()
    study_id    = fields.Many2one('onevoice.bible.study')
