from odoo import models, fields, api


class OneVoiceVolunteer(models.Model):
    _name = 'onevoice.volunteer'
    _description = 'OneVoice27 Volunteer Registration'
    _order = 'create_date desc'
    _rec_name = 'name'

    name         = fields.Char(string='Full Name', required=True)
    email        = fields.Char(string='Email')
    phone        = fields.Char(string='Phone')
    city         = fields.Char(string='City / Region')
    roles        = fields.Char(string='Service Roles')
    availability = fields.Char(string='Availability')
    notes        = fields.Text(string='Additional Notes')
    state        = fields.Selection([
        ('new',       'New'),
        ('contacted', 'Contacted'),
        ('active',    'Active Volunteer'),
    ], string='Status', default='new', required=True)
    partner_id = fields.Many2one('res.partner', string='Related Contact')

    def action_set_contacted(self):
        self.write({'state': 'contacted'})

    def action_set_active(self):
        self.write({'state': 'active'})

    @api.model
    def app_submit_volunteer(self, vals):
        """Called from the Flutter app to create or update a volunteer record."""
        data = {
            'name':         vals.get('name', ''),
            'email':        vals.get('email', ''),
            'phone':        vals.get('phone', ''),
            'city':         vals.get('city', ''),
            'roles':        vals.get('roles', ''),
            'availability': vals.get('availability', ''),
            'notes':        vals.get('notes', ''),
        }
        record_id = vals.get('record_id')
        if record_id:
            record = self.sudo().browse(int(record_id))
            if record.exists():
                record.write(data)
                return {'id': record.id, 'status': 'updated'}
        record = self.sudo().create(data)
        return {'id': record.id, 'status': 'created'}

    @api.model
    def app_get_volunteer(self, record_id):
        """Fetch a volunteer record by ID for the Flutter app."""
        record = self.sudo().browse(int(record_id))
        if not record.exists():
            return {}
        return {
            'id':           record.id,
            'name':         record.name or '',
            'email':        record.email or '',
            'phone':        record.phone or '',
            'city':         record.city or '',
            'roles':        record.roles or '',
            'availability': record.availability or '',
            'notes':        record.notes or '',
        }
