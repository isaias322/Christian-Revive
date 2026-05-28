# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OnevoicePrayerWall(models.Model):
    _name        = 'onevoice.prayer.wall'
    _description = 'Prayer Wall Request'
    _order       = 'posted_date desc'

    name         = fields.Char(string='Name',           required=True, default='Anonymous')
    request_text = fields.Text(string='Prayer Request', required=True)
    pray_count   = fields.Integer(string='Praying for You', default=0)
    posted_date  = fields.Datetime(string='Posted', default=fields.Datetime.now)
    is_active    = fields.Boolean(string='Active', default=True)
    session_key  = fields.Char(string='Session Key')

    # ── App API ──────────────────────────────────────────────────

    @api.model
    def app_submit_request(self, vals):
        """Create a public prayer wall request from the Flutter app."""
        record = self.sudo().create({
            'name':         vals.get('name', 'Anonymous'),
            'request_text': vals.get('request', ''),
            'posted_date':  fields.Datetime.now(),
            'session_key':  vals.get('session_key', ''),
        })
        return {
            'id':      record.id,
            'name':    record.name,
            'request': record.request_text,
            'date':    record.posted_date.isoformat(),
            'prays':   record.pray_count,
        }

    @api.model
    def app_get_requests(self):
        """Return all active prayer requests (public — all users see these)."""
        records = self.sudo().search(
            [('is_active', '=', True)],
            order='posted_date desc',
            limit=200,
        )
        return [
            {
                'id':          r.id,
                'name':        r.name or 'Anonymous',
                'request':     r.request_text or '',
                'date':        r.posted_date.isoformat() if r.posted_date else '',
                'prays':       r.pray_count,
                'session_key': r.session_key or '',
            }
            for r in records
        ]

    @api.model
    def app_pray_for(self, request_id):
        """Increment the pray count for a request."""
        record = self.sudo().browse(int(request_id))
        if record.exists() and record.is_active:
            record.pray_count += 1
            return {'pray_count': record.pray_count}
        return {'pray_count': 0}

    @api.model
    def app_delete_request(self, request_id, session_key):
        """Delete a request only if it belongs to this session."""
        record = self.sudo().search([
            ('id',          '=', int(request_id)),
            ('session_key', '=', session_key),
        ], limit=1)
        if record:
            record.unlink()
            return True
        return False
