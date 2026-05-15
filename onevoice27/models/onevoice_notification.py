# -*- coding: utf-8 -*-
import json
import logging
import requests
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class OneVoiceNotification(models.Model):
    _name        = 'onevoice.notification'
    _description = 'OneVoice27 Push Notification'
    _order       = 'create_date desc'
    _rec_name    = 'title'

    title       = fields.Char(string='Title',   required=True)
    message     = fields.Text(string='Message', required=True)
    target      = fields.Selection([
        ('all',    'All OneVoice27 Users'),
        ('device', 'Specific Device'),
    ], string='Send To', required=True, default='all')
    device_id   = fields.Many2one(
        'onevoice.device', string='Device',
        domain=[],
        help='Required when "Send To" is set to Specific Device',
    )
    status      = fields.Selection([
        ('draft', 'Draft'),
        ('sent',  'Sent'),
        ('error', 'Error'),
    ], string='Status', default='draft', readonly=True)
    sent_at     = fields.Datetime(string='Sent At', readonly=True)
    error_msg   = fields.Text(string='Error Detail', readonly=True)
    sent_count  = fields.Integer(string='Devices Reached', readonly=True, default=0)

    # ── Constraints ─────────────────────────────────────────────
    @api.constrains('target', 'device_id')
    def _check_device(self):
        for rec in self:
            if rec.target == 'device' and not rec.device_id:
                raise UserError('Please select a device when "Send To" is Specific Device.')

    # ── Send action ─────────────────────────────────────────────
    def action_send(self):
        self.ensure_one()
        if self.status == 'sent':
            raise UserError('This notification has already been sent.')

        server_key = self.env['ir.config_parameter'].sudo().get_param(
            'onevoice27.fcm_server_key', ''
        )
        if not server_key:
            raise UserError(
                'FCM Server Key not configured.\n\n'
                'Go to Settings → Technical → System Parameters and add:\n'
                '  Key:   onevoice27.fcm_server_key\n'
                '  Value: <your Firebase Server Key>'
            )

        if self.target == 'all':
            self._send_to_topic(server_key)
        else:
            self._send_to_device(server_key)

    def _build_payload(self, registration_id=None, topic=None):
        notification = {
            'title': self.title,
            'body':  self.message,
        }
        data = {
            'type':    'ov27_push',
            'title':   self.title,
            'body':    self.message,
            'notif_id': str(self.id),
        }
        payload = {
            'notification': notification,
            'data':         data,
            'priority':     'high',
        }
        if topic:
            payload['to'] = f'/topics/{topic}'
        elif registration_id:
            payload['to'] = registration_id
        return payload

    def _fcm_post(self, server_key, payload):
        url = 'https://fcm.googleapis.com/fcm/send'
        headers = {
            'Authorization': f'key={server_key}',
            'Content-Type':  'application/json',
        }
        try:
            resp = requests.post(url, headers=headers,
                                 data=json.dumps(payload), timeout=10)
            resp.raise_for_status()
            result = resp.json()
            _logger.info('FCM response: %s', result)
            return result
        except Exception as exc:
            _logger.error('FCM send failed: %s', exc)
            raise

    def _send_to_topic(self, server_key):
        payload = self._build_payload(topic='revive_ov27')
        try:
            result = self._fcm_post(server_key, payload)
            # Topic sends return message_id, not success count
            self.write({
                'status':     'sent',
                'sent_at':    fields.Datetime.now(),
                'sent_count': 1,
                'error_msg':  False,
            })
        except Exception as exc:
            self.write({'status': 'error', 'error_msg': str(exc)})
            raise UserError(f'FCM send failed: {exc}')

    def _send_to_device(self, server_key):
        token = self.device_id.fcm_token
        if not token:
            raise UserError('Selected device has no FCM token.')
        payload = self._build_payload(registration_id=token)
        try:
            result = self._fcm_post(server_key, payload)
            success = result.get('success', 0)
            self.write({
                'status':     'sent' if success else 'error',
                'sent_at':    fields.Datetime.now(),
                'sent_count': success,
                'error_msg':  None if success else json.dumps(result.get('results', [])),
            })
            if not success:
                raise UserError(f'FCM rejected the token: {result}')
        except UserError:
            raise
        except Exception as exc:
            self.write({'status': 'error', 'error_msg': str(exc)})
            raise UserError(f'FCM send failed: {exc}')

    def action_reset_draft(self):
        self.ensure_one()
        self.write({'status': 'draft', 'error_msg': False})
