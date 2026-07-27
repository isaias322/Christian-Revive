# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request

from .base import (API, api_endpoint, get_json_body, json_response)

_logger = logging.getLogger(__name__)


class MarketplaceApiAuth(http.Controller):

    def _verify_credentials(self, login, password, include_inactive=False):
        """Version-tolerant password check. Returns res.users or None.

        include_inactive=True is used to distinguish "wrong password"
        from "correct password, account still pending email
        verification" - active_test excludes pending accounts from the
        default search, so login() needs a way to still check their
        password without letting them actually authenticate."""
        query = request.env['res.users'].sudo()
        if include_inactive:
            query = query.with_context(active_test=False)
        user = query.search([('login', '=', login)], limit=1)
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
        Users = request.env['res.users'].sudo()
        existing = Users.with_context(active_test=False).search(
            [('login', '=', email)], limit=1)
        if existing and existing.active:
            return json_response(
                error='An account with this email already exists.',
                status=409, error_code='duplicate')
        if existing and not existing.active:
            # Someone started signing up with this email but never
            # verified it - let them retry (e.g. fix a typo'd password)
            # rather than getting stuck, and just send a fresh link.
            existing.write({'name': name, 'password': password})
            self._send_verification(existing.partner_id)
            return json_response({
                'pending_verification': True, 'email': email,
            }, status=200)
        Users._signup_create_user({
            'name': name, 'login': email, 'email': email,
            'password': password,
        })
        user = Users.with_context(active_test=False).search(
            [('login', '=', email)], limit=1)
        if not user:
            return json_response(
                error='Account creation failed — try again.',
                status=500, error_code='server_error')
        # Held inactive until the email link is clicked - _signup_create_user
        # always creates active accounts, so flip it back off here.
        user.active = False
        self._send_verification(user.partner_id)
        return json_response({
            'pending_verification': True, 'email': email,
        }, status=201)

    def _send_verification(self, partner):
        try:
            request.env['marketplace.email.verification'].sudo().send_verification_email(
                partner, request.httprequest.url_root)
        except Exception:
            _logger.exception(
                'Failed to send verification email to %s', partner.email)

    @http.route(API + '/auth/resend-verification', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=False)
    def resend_verification(self, api_user=None, **kw):
        """Public and email-based (not Bearer-token auth'd): a pending
        account has no token to authenticate with yet. Always returns
        the same response regardless of whether the email is registered,
        so this can't be used to enumerate accounts."""
        body = get_json_body()
        email = (body.get('email') or '').strip().lower()
        if email:
            user = request.env['res.users'].sudo().with_context(
                active_test=False).search([('login', '=', email)], limit=1)
            if user and not user.active:
                self._send_verification(user.partner_id)
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
            pending = self._verify_credentials(
                email, password, include_inactive=True)
            if pending and not pending.active:
                return json_response(
                    error='Please verify your email before logging in. '
                          'Check your inbox, or request a new link.',
                    status=403, error_code='email_not_verified')
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
        body = get_json_body()
        device_token = (body.get('device_token') or '').strip()
        if device_token:
            request.env['marketplace.device.token'].sudo().unregister(device_token)
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
