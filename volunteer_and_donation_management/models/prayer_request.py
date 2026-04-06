from odoo import models, fields, api


class PrayerRequest(models.Model):
    _name = 'prayer.request'
    _description = 'Prayer Request'
    _order = 'create_date desc'

    name = fields.Char(string='Requester Name', required=True)
    email = fields.Char(string='Email')
    subject = fields.Char(string='Subject', required=True)
    message = fields.Text(string='Message', required=True)
    state = fields.Selection([
        ('request', 'Request'),
        ('prayed', 'Prayed'),
    ], string='Status', default='request')
    pray_count = fields.Integer(string='Prayer Count', default=0)
    is_published = fields.Boolean(string='Published', default=True)
    partner_id = fields.Many2one('res.partner', string='Submitted By')

    prayed_by = fields.Text(string='Prayed By', default='')

    # Response fields
    response = fields.Text(string='Response')
    response_by = fields.Char(string='Response By')
    response_date = fields.Datetime(string='Response Date')

    def action_mark_prayed(self):
        """Increment pray count from the app"""
        for rec in self:
            rec.sudo().write({
                'pray_count': rec.pray_count + 1,
            })
        return True

    def action_respond(self, response_text, responded_by=''):
        """Called from the Flutter app (pastor) or Odoo backend to add a response"""
        for rec in self:
            rec.sudo().write({
                'response': response_text,
                'response_by': responded_by or self.env.user.name,
                'response_date': fields.Datetime.now(),
                'state': 'prayed',
            })
        return True

    @api.model
    def app_submit_prayer(self, vals):
        """Called from the Flutter app to create a prayer request"""
        record = self.sudo().create(vals)
        return {
            'id': record.id,
            'name': record.name,
            'subject': record.subject,
            'message': record.message,
            'state': record.state,
            'pray_count': record.pray_count,
            'create_date': str(record.create_date),
        }
    
    def action_mark_prayed(self, prayed_by_name=''):
        for rec in self:
            existing = rec.prayed_by or ''
            if prayed_by_name:
                names = [n.strip() for n in existing.split(',') if n.strip()]
                if prayed_by_name not in names:
                    names.append(prayed_by_name)
                existing = ', '.join(names)
            rec.sudo().write({
                'pray_count': rec.pray_count + 1,
                'prayed_by': existing,
            })
        return True