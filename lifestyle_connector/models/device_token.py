# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LifestyleDeviceToken(models.Model):
    _name = 'lifestyle.device.token'
    _description = 'Customer FCM Device Token'
    _rec_name = 'token'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, index=True, ondelete='cascade')
    token = fields.Char(string='FCM Token', required=True, index=True)
    platform = fields.Selection([('android', 'Android'), ('ios', 'iOS')], string='Platform', default='android')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('token_unique', 'unique(token)', 'This device token is already registered.'),
    ]

    @api.model
    def register(self, partner, token, platform='android'):
        existing = self.search([('token', '=', token)], limit=1)
        if existing:
            existing.write({'partner_id': partner.id, 'platform': platform, 'active': True})
            return existing
        return self.create({'partner_id': partner.id, 'token': token, 'platform': platform})
