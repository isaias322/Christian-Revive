# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request

from .base import (API, api_endpoint, get_json_body, json_response)

_logger = logging.getLogger(__name__)


class MarketplaceApiAuth(http.Controller):

    def _verify_credentials(self, login, password):
        """Version-tolerant password check. Returns res.users or None."""
        user = request.env['res.users'].sudo().search(
            [('login', '=', login)], limit=1)
        if not user or not password:
            return None
        user_as = user.with_user(user)
        env_info = {'interactive': False}
        credential = {'login': login, 'password': password, 'type': 'password'}
        try:
            try:
                user_as._check_credentials(credential, env_info)
            except TypeError:
                # Older signature: (password, env)
                user_as._check_credentials(password, env_info)
        except AccessDenied:
            return None
        return user

    @http.route(API + '/auth/register', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=False)
    def register(self, api_user=None, **kw):
        body = get_json_body()
        name = (body.get('name') or '').strip()
        email = (body.get('email') or '').strip().lower()
        password = body.get('password') or ''
        if not name or not email or len(password) < 8:
            return json_response(
                error='Name, email and a password of at least 8 characters '
                      'are required.', status=400, error_code='validation')
        existing = request.env['res.users'].sudo().search(
            [('login', '=', email)], limit=1)
        if existing:
            return json_response(
                error='An account with this email already exists.',
                status=409, error_code='duplicate')
        request.env['res.users'].sudo()._signup_create_user({
            'name': name,
            'login': email,
            'email': email,
            'password': password,
        })
        user = self._verify_credentials(email, password)
        if not user:
            return json_response(
                error='Account created but login failed — try logging in.',
                status=500, error_code='server_error')
        token = request.env['marketplace.api.token'].issue(
            user, body.get('device_name'))
        try:
            request.env['marketplace.email.verification'].sudo().send_verification_email(
                user.partner_id, request.httprequest.url_root)
        except Exception:
            _logger.exception(
                'Failed to send verification email to %s', email)
        return json_response({
            'token': token.token,
            'user': self._serialize_user(user),
        }, status=201)

    @http.route(API + '/auth/resend-verification', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def resend_verification(self, api_user=None, **kw):
        partner = api_user.partner_id
        if partner.marketplace_email_verified:
            return json_response({'already_verified': True})
        try:
            request.env['marketplace.email.verification'].sudo().send_verification_email(
                partner, request.httprequest.url_root)
        except Exception:
            _logger.exception(
                'Failed to resend verification email to %s', partner.email)
            return json_response(
                error='Could not send the email right now — try again '
                      'shortly.', status=500, error_code='server_error')
        return json_response({'sent': True})

    @http.route(API + '/auth/login', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=False)
    def login(self, api_user=None, **kw):
        body = get_json_body()
        email = (body.get('email') or '').strip().lower()
        password = body.get('password') or ''
        user = self._verify_credentials(email, password)
        if not user:
            return json_response(error='Invalid email or password.',
                                 status=401, error_code='bad_credentials')
        token = request.env['marketplace.api.token'].issue(
            user, body.get('device_name'))
        return json_response({
            'token': token.token,
            'user': self._serialize_user(user),
        })

    @http.route(API + '/auth/logout', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def logout(self, api_user=None, **kw):
        header = request.httprequest.headers.get('Authorization', '')
        token = header[7:].strip() if header.lower().startswith('bearer ') else ''
        request.env['marketplace.api.token'].revoke(token)
        return json_response({'logged_out': True})

    @http.route(API + '/me', type='http', auth='public',
                methods=['GET'], csrf=False)
    @api_endpoint(auth_required=True)
    def me(self, api_user=None, **kw):
        return json_response(self._serialize_user(api_user))

    @http.route(API + '/me', type='http', auth='public',
                methods=['PUT', 'PATCH'], csrf=False)
    @api_endpoint(auth_required=True)
    def update_me(self, api_user=None, **kw):
        body = get_json_body()
        partner = api_user.partner_id.sudo()
        vals = {}
        for field in ('name', 'phone', 'street', 'city', 'zip'):
            if field in body:
                vals[field] = body[field] or False
        if vals.get('name') is False:
            vals.pop('name')
        if vals:
            partner.write(vals)
        return json_response(self._serialize_user(api_user))

    @http.route(API + '/device-token', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def register_device_token(self, api_user=None, **kw):
        """Registers this device for push notifications (made-to-order
        progress updates, etc). No-op-safe: works whether or not Firebase
        has actually been configured on the server yet."""
        body = get_json_body()
        token = (body.get('token') or '').strip()
        if not token:
            return json_response(error='Token is required.', status=400,
                                 error_code='validation')
        request.env['marketplace.device.token'].sudo().register(
            api_user.partner_id, token, platform=body.get('platform'))
        return json_response({'registered': True})

    def _serialize_user(self, user):
        partner = user.partner_id
        seller = partner.sudo().get_marketplace_seller()
        return {
            'id': user.id,
            'name': partner.name,
            'email': user.login,
            'phone': partner.phone or None,
            'street': partner.street or None,
            'city': partner.city or None,
            'zip': partner.zip or None,
            'has_shop': bool(seller),
            'shop_id': seller.id or None,
            'shop_state': seller.state if seller else None,
            'email_verified': partner.marketplace_email_verified,
        }
