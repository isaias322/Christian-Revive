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
    completed_session_count = fields.Integer(string='Completed Sessions', default=0)
    completed_session_ids = fields.Text(string='Completed Session IDs')
    total_session_count = fields.Integer(string='Total Sessions', default=121)
    certificate_eligible = fields.Boolean(
        string='Certificate Eligible',
        compute='_compute_certificate_eligible',
        store=True,
    )
    certificate_issued = fields.Boolean(string='Certificate Issued', default=False)
    certificate_issued_date = fields.Datetime(string='Certificate Issued On')
    prayer_pledge_count = fields.Integer(string='Prayer Pledges', default=0)
    testimony_count = fields.Integer(string='Testimonies', default=0)
    prayer_pledges_details = fields.Text(string='Prayer Pledge Details')
    testimonies_details = fields.Text(string='Testimony Details')

    @api.depends('completed_session_count', 'total_session_count')
    def _compute_certificate_eligible(self):
        for record in self:
            record.certificate_eligible = (
                record.total_session_count > 0
                and record.completed_session_count >= record.total_session_count
            )

    def action_set_interested(self):
        self.write({'state': 'interested'})

    def action_set_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_set_completed(self):
        self.write({'state': 'completed'})

    def action_mark_certificate_issued(self):
        self.write({
            'certificate_issued': True,
            'certificate_issued_date': fields.Datetime.now(),
        })

    @api.model
    def app_update_pledge_testimony_count(self, record_id, prayer_pledge_count, testimony_count,
                                          prayer_pledges_details=None, testimonies_details=None):
        record = self.sudo().browse(record_id)
        if not record.exists():
            return {'error': 'Record not found'}
        vals = {
            'prayer_pledge_count': prayer_pledge_count,
            'testimony_count': testimony_count,
        }
        if prayer_pledges_details is not None:
            vals['prayer_pledges_details'] = prayer_pledges_details
        if testimonies_details is not None:
            vals['testimonies_details'] = testimonies_details
        record.write(vals)
        return {'success': True, 'id': record.id}

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
            'completed_session_count': record.completed_session_count,
            'completed_session_ids': record.completed_session_ids or '',
            'total_session_count': record.total_session_count,
            'certificate_eligible': record.certificate_eligible,
            'certificate_issued': record.certificate_issued,
            'prayer_pledge_count': record.prayer_pledge_count,
            'testimony_count': record.testimony_count,
            'create_date': str(record.create_date),
        }
