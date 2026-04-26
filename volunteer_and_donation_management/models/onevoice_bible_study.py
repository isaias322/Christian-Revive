from odoo import models, fields, api


class OneVoiceBibleStudy(models.Model):
    _name = 'onevoice.bible.study'
    _description = 'OneVoice27 Bible Study Registration'
    _order = 'create_date desc'
    _rec_name = 'contact_name'

    contact_name = fields.Char(string='Contact Name', required=True)
    phone = fields.Char(string='Phone')
    location = fields.Char(string='Location / City')
    study_days = fields.Char(string='Study Days')
    state = fields.Selection([
        ('interested', 'Interested'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='Status', default='interested', required=True)
    notes = fields.Text(string='Notes')
    partner_id = fields.Many2one('res.partner', string='Related Contact')

    def action_set_interested(self):
        self.write({'state': 'interested'})

    def action_set_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_set_completed(self):
        self.write({'state': 'completed'})

    @api.model
    def app_create_registration(self, vals):
        record = self.sudo().create(vals)
        return {
            'id': record.id,
            'contact_name': record.contact_name,
            'phone': record.phone or '',
            'location': record.location or '',
            'study_days': record.study_days or '',
            'state': record.state,
            'create_date': str(record.create_date),
        }
