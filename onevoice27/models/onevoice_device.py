# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime


class OneVoiceDevice(models.Model):
    _name        = 'onevoice.device'
    _description = 'OneVoice27 App Device (FCM token registry)'
    _order       = 'last_seen desc'
    _rec_name    = 'display_name'

    session_key  = fields.Char(string='Session Key', required=True, index=True)
    fcm_token    = fields.Char(string='FCM Token',   required=True)
    device_label = fields.Char(string='Device Label')   # e.g. "Isaias – iPhone"
    last_seen    = fields.Datetime(string='Last Seen', default=fields.Datetime.now)
    display_name = fields.Char(string='Name', compute='_compute_display', store=True)

    @api.depends('device_label', 'session_key')
    def _compute_display(self):
        for rec in self:
            rec.display_name = rec.device_label or f'Device …{rec.session_key[-6:]}' if rec.session_key else 'Unknown'

    @api.model
    def app_register_device(self, vals):
        """
        Called from Flutter on every app start.
        vals = {session_key, fcm_token, device_label (optional)}
        Creates or updates the device record.
        """
        session_key = vals.get('session_key', '').strip()
        fcm_token   = vals.get('fcm_token',   '').strip()
        if not session_key or not fcm_token:
            return {'status': 'error', 'message': 'session_key and fcm_token required'}

        existing = self.sudo().search([('session_key', '=', session_key)], limit=1)
        data = {
            'fcm_token': fcm_token,
            'last_seen': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        }
        if vals.get('device_label'):
            data['device_label'] = vals['device_label']

        if existing:
            existing.write(data)
            return {'status': 'updated', 'id': existing.id}

        data['session_key'] = session_key
        record = self.sudo().create(data)
        return {'status': 'created', 'id': record.id}
