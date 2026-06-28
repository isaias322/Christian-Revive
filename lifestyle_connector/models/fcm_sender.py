# -*- coding: utf-8 -*-
import json
import logging

import requests

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

FCM_CONFIG_PARAM = 'lifestyle_connector.fcm_service_account_path'


class LifestyleFcmMixin(models.AbstractModel):
    """Shared Firebase Cloud Messaging (v1 API) sender, following the same
    google-auth service-account pattern already used by the onevoice27 module."""
    _name = 'lifestyle.fcm.mixin'
    _description = 'Lifestyle FCM Sender Mixin'

    def _lifestyle_get_fcm_credentials(self):
        sa_path = self.env['ir.config_parameter'].sudo().get_param(FCM_CONFIG_PARAM, '')
        if not sa_path:
            raise UserError(
                'FCM Service Account not configured.\n\n'
                'Go to Settings > Technical > Parameters > System Parameters and add:\n'
                f'  Key:   {FCM_CONFIG_PARAM}\n'
                '  Value: /path/to/lifestyle_fcm_service_account.json\n\n'
                'Download the JSON from Firebase Console > Project Settings > Service Accounts.'
            )
        try:
            from google.oauth2 import service_account
            import google.auth.transport.requests as gatr

            with open(sa_path, 'r') as f:
                sa_info = json.load(f)

            project_id = sa_info.get('project_id', '')
            if not project_id:
                raise UserError('project_id not found in FCM service account JSON.')

            creds = service_account.Credentials.from_service_account_info(
                sa_info,
                scopes=['https://www.googleapis.com/auth/firebase.messaging'],
            )
            creds.refresh(gatr.Request())
            return creds.token, project_id
        except ImportError:
            raise UserError('The google-auth library is not installed on the server.')
        except UserError:
            raise
        except Exception as exc:
            raise UserError(f'Failed to load FCM credentials: {exc}')

    def _lifestyle_build_payload(self, token, title, body, data=None, image_url=None):
        notification = {'title': title, 'body': body}
        if image_url:
            notification['image'] = image_url
        message = {
            'token': token,
            'notification': notification,
            'data': {k: str(v) for k, v in (data or {}).items()},
            'android': {
                'priority': 'high',
                'notification': {'sound': 'default', **({'image': image_url} if image_url else {})},
            },
            'apns': {
                'payload': {'aps': {'sound': 'default', 'mutable-content': 1}},
                'fcm_options': ({'image': image_url} if image_url else {}),
            },
        }
        return {'message': message}

    def _lifestyle_fcm_post(self, access_token, project_id, payload):
        url = f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            _logger.error('FCM v1 send failed: %s', exc)
            raise


    def _lifestyle_send_push_to_employee(self, employee, title, body, data=None, image_url=None):
        """Send a push notification to every active vendor device for this employee."""
        tokens = self.env['lifestyle.device.token'].sudo().search([
            ('employee_id', '=', employee.id),
            ('active', '=', True),
        ])
        if not tokens:
            _logger.info('No FCM device tokens for employee %s, skipping push.', employee.id)
            return 0

        access_token, project_id = self._lifestyle_get_fcm_credentials()
        sent = 0
        for device in tokens:
            payload = self._lifestyle_build_payload(device.token, title, body, data=data, image_url=image_url)
            try:
                self._lifestyle_fcm_post(access_token, project_id, payload)
                sent += 1
            except Exception as exc:
                _logger.warning('Push to vendor device %s failed: %s', device.id, exc)
        return sent

    def _lifestyle_send_push_to_partner(self, partner, title, body, data=None, image_url=None):
        """Send a push notification to every active device registered for this partner."""
        tokens = self.env['lifestyle.device.token'].sudo().search([
            ('partner_id', '=', partner.id),
            ('active', '=', True),
        ])
        if not tokens:
            _logger.info('No FCM device tokens for partner %s, skipping push.', partner.id)
            return 0

        access_token, project_id = self._lifestyle_get_fcm_credentials()
        sent = 0
        for device in tokens:
            payload = self._lifestyle_build_payload(device.token, title, body, data=data, image_url=image_url)
            try:
                self._lifestyle_fcm_post(access_token, project_id, payload)
                sent += 1
            except Exception as exc:
                _logger.warning('Push to device %s failed: %s', device.id, exc)
        return sent
