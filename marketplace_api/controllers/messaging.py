# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

from .base import (API, api_endpoint, get_json_body, json_response,
                   serialize_message, serialize_thread)


class MarketplaceApiMessaging(http.Controller):

    def _thread(self, thread_id, api_user):
        thread = request.env['marketplace.thread'].sudo().browse(thread_id)
        if not thread.exists() or not thread.partner_can_access(
                api_user.partner_id):
            raise request.not_found()
        return thread

    @http.route(API + '/threads', type='http', auth='public',
                methods=['GET'], csrf=False)
    @api_endpoint(auth_required=True)
    def threads(self, api_user=None, **kw):
        partner = api_user.partner_id
        records = request.env['marketplace.thread'].sudo().search([
            '|', ('buyer_partner_id', '=', partner.id),
            ('seller_id.partner_id', '=', partner.id)])
        return json_response({
            'items': [serialize_thread(t, partner) for t in records],
        })

    @http.route(API + '/threads', type='http', auth='public',
                methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def start_thread(self, api_user=None, **kw):
        body = get_json_body()
        seller = request.env['marketplace.seller'].sudo().browse(
            int(body.get('seller_id') or 0))
        if not seller.exists():
            raise request.not_found()
        listing = None
        if body.get('listing_id'):
            listing = request.env['product.template'].sudo().browse(
                int(body['listing_id']))
            listing = listing if listing.exists() else None
        thread = request.env['marketplace.thread'].get_or_create_thread(
            api_user.partner_id, seller, listing)
        if body.get('message'):
            thread.post_message(api_user.partner_id, body['message'])
        return json_response(
            serialize_thread(thread, api_user.partner_id), status=201)

    @http.route(API + '/threads/<int:thread_id>/messages', type='http',
                auth='public', methods=['GET'], csrf=False)
    @api_endpoint(auth_required=True)
    def messages(self, thread_id, api_user=None, after='0', **kw):
        thread = self._thread(thread_id, api_user)
        partner = api_user.partner_id
        after_id = int(after) if str(after).isdigit() else 0
        records = thread.message_ids.filtered(lambda m: m.id > after_id)
        thread.mark_read(partner)
        return json_response({
            'thread': serialize_thread(thread, partner),
            'items': [serialize_message(m, partner) for m in records],
        })

    @http.route(API + '/threads/<int:thread_id>/messages', type='http',
                auth='public', methods=['POST'], csrf=False)
    @api_endpoint(auth_required=True)
    def post_message(self, thread_id, api_user=None, **kw):
        thread = self._thread(thread_id, api_user)
        body = get_json_body()
        image = body.get('image')
        if image and ',' in image[:64] and image.strip().startswith('data:'):
            image = image.split(',', 1)[1]
        message = thread.post_message(
            api_user.partner_id, body.get('body') or '',
            image=image, image_filename=body.get('image_filename'))
        return json_response(
            serialize_message(message, api_user.partner_id), status=201)
