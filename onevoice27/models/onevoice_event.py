# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OnevoiceEvent(models.Model):
    _name        = 'onevoice.event'
    _description = 'OneVoice27 Event'
    _order       = 'date_start asc'
    _rec_name    = 'name'

    name              = fields.Char(string='Event Title', required=True)
    category          = fields.Selection([
        ('worship',   'Worship'),
        ('prayer',    'Prayer'),
        ('baptism',   'Baptism'),
        ('seminar',   'Seminar'),
        ('youth',     'Youth'),
        ('community', 'Community'),
        ('other',     'Other'),
    ], string='Category', default='other')
    date_start        = fields.Datetime(string='Start Date & Time', required=True)
    date_end          = fields.Datetime(string='End Date & Time')
    location          = fields.Char(string='Location / Venue')
    description       = fields.Html(string='Description')
    image             = fields.Image(string='Event Banner', max_width=1200, max_height=800)
    registration_link = fields.Char(string='Registration Link')
    is_active         = fields.Boolean(string='Active (Visible in App)', default=True)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end and rec.date_start and rec.date_end < rec.date_start:
                from odoo.exceptions import ValidationError
                raise ValidationError('End date cannot be before start date.')

    # ── App API ──────────────────────────────────────────────────

    @api.model
    def app_get_events(self, limit=100, offset=0):
        """Return active events for the Flutter app ordered by date."""
        records = self.sudo().search(
            [('is_active', '=', True)],
            order='date_start asc',
            limit=limit,
            offset=offset,
        )
        return [
            {
                'id':                r.id,
                'name':              r.name or '',
                'category':          r.category or '',
                'date_start':        r.date_start.isoformat() if r.date_start else '',
                'date_end':          r.date_end.isoformat() if r.date_end else '',
                'location':          r.location or '',
                'description':       r.description or '',
                'registration_link': r.registration_link or '',
                'has_image':         bool(r.image),
            }
            for r in records
        ]
