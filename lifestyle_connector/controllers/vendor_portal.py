# -*- coding: utf-8 -*-
import base64
from datetime import timedelta
from urllib.parse import quote

from odoo import fields, http
from odoo.http import request

from ..models.sale_order import STAGE_LABELS, DELIVERY_STAGE_SEQUENCE, PICKUP_STAGE_SEQUENCE

SESSION_KEY = 'lifestyle_vendor_token'


def _web_vendor_employee():
    """Mirrors api.py's _vendor_employee(), but reads the vendor session
    token from the browser's Odoo session instead of a custom HTTP header -
    a website visitor can't easily set custom headers across page loads,
    while a session survives normal link clicks and form posts."""
    token = request.session.get(SESSION_KEY)
    if not token:
        return None
    vendor_session = request.env['lifestyle.vendor.session'].sudo().search([('token', '=', token)], limit=1)
    if not vendor_session:
        return None
    employee = vendor_session.employee_id
    if not employee.is_app_active or employee.staff_role != 'carpenter':
        return None
    return employee


class LifestyleVendorPortal(http.Controller):

    @http.route('/vendor/login', type='http', auth='public', website=True, methods=['GET'], csrf=True)
    def vendor_login_form(self, **kwargs):
        if _web_vendor_employee():
            return request.redirect('/vendor/orders')
        return request.render('lifestyle_connector.vendor_portal_login', {'error': kwargs.get('error')})

    @http.route('/vendor/login/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def vendor_login_submit(self, email=None, pin=None, **kwargs):
        employee = request.env['hr.employee'].sudo().search([('app_email', '=', email)], limit=1)
        error = None
        if not employee:
            error = 'Invalid email or PIN.'
        elif employee.app_pin_locked_until and employee.app_pin_locked_until > fields.Datetime.now():
            error = 'Too many failed attempts. Try again in a few minutes.'
        elif not employee.is_app_active or employee.app_pin != pin:
            employee.app_pin_failed_attempts += 1
            if employee.app_pin_failed_attempts >= 5:
                employee.app_pin_locked_until = fields.Datetime.now() + timedelta(minutes=15)
                employee.app_pin_failed_attempts = 0
            error = 'Invalid email or PIN.'
        elif employee.staff_role != 'carpenter':
            error = 'This account does not have vendor access.'

        if error:
            return request.render('lifestyle_connector.vendor_portal_login', {'error': error})

        employee.app_pin_failed_attempts = 0
        employee.app_pin_locked_until = False
        vendor_session = request.env['lifestyle.vendor.session'].sudo().issue_for(employee)
        request.session[SESSION_KEY] = vendor_session.token
        return request.redirect('/vendor/orders')

    @http.route('/vendor/logout', type='http', auth='public', website=True, methods=['GET'])
    def vendor_logout(self, **kwargs):
        request.session.pop(SESSION_KEY, None)
        return request.redirect('/vendor/login')

    @http.route('/vendor/orders', type='http', auth='public', website=True, methods=['GET'])
    def vendor_orders_list(self, **kwargs):
        employee = _web_vendor_employee()
        if not employee:
            return request.redirect('/vendor/login')
        orders = request.env['sale.order'].sudo().search(
            [('lifestyle_vendor_id', '=', employee.id)], order='date_order desc', limit=50,
        )
        return request.render('lifestyle_connector.vendor_portal_orders', {
            'employee': employee,
            'orders': orders,
            'stage_labels': STAGE_LABELS,
        })

    @http.route('/vendor/orders/<int:order_id>', type='http', auth='public', website=True, methods=['GET'])
    def vendor_order_detail(self, order_id, **kwargs):
        employee = _web_vendor_employee()
        if not employee:
            return request.redirect('/vendor/login')
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.lifestyle_vendor_id.id != employee.id:
            return request.redirect('/vendor/orders')

        stages = PICKUP_STAGE_SEQUENCE if order.fulfillment_type == 'pickup' else DELIVERY_STAGE_SEQUENCE
        if order._lifestyle_skip_processing():
            stages = [stage for stage in stages if stage != 'processing']
        available_stages = [stage for stage in stages if stage != 'order_placed']

        return request.render('lifestyle_connector.vendor_portal_order_detail', {
            'employee': employee,
            'order': order,
            'available_stages': available_stages,
            'stage_labels': STAGE_LABELS,
            'media_list': order._lifestyle_media_list(),
            'error': kwargs.get('error'),
        })

    @http.route('/vendor/orders/<int:order_id>/stage', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def vendor_order_update_stage(self, order_id, stage=None, **kwargs):
        employee = _web_vendor_employee()
        if not employee:
            return request.redirect('/vendor/login')
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.lifestyle_vendor_id.id != employee.id:
            return request.redirect('/vendor/orders')
        try:
            order._lifestyle_advance_stage(stage, push=False)
        except Exception as exc:
            return request.redirect(f'/vendor/orders/{order_id}?error={quote(str(exc))}')
        return request.redirect(f'/vendor/orders/{order_id}')

    @http.route('/vendor/orders/<int:order_id>/media', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def vendor_order_send_media(self, order_id, comment=None, **kwargs):
        employee = _web_vendor_employee()
        if not employee:
            return request.redirect('/vendor/login')
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.lifestyle_vendor_id.id != employee.id:
            return request.redirect('/vendor/orders')
        if not order._lifestyle_can_send_media():
            return request.redirect(f'/vendor/orders/{order_id}?error=This+order+has+already+been+completed.')

        stage_label = STAGE_LABELS.get(order.delivery_stage, order.delivery_stage)
        uploaded = request.httprequest.files.getlist('media')
        created = 0
        for file in uploaded:
            if not file or not file.filename:
                continue
            data = file.read()
            if not data:
                continue
            mimetype = file.mimetype or 'application/octet-stream'
            if not mimetype.startswith(('image/', 'video/')):
                continue
            created += 1
            request.env['ir.attachment'].sudo().create({
                'name': file.filename,
                'res_model': 'sale.order',
                'res_id': order.id,
                'mimetype': mimetype,
                'datas': base64.b64encode(data),
                'description': (comment or '').strip() or False,
                'lifestyle_stage_label': stage_label,
            })

        comment = (comment or '').strip()
        if created or comment:
            try:
                order.action_send_media_update(new_count=created or 1, comment=comment or None)
            except Exception as exc:
                return request.redirect(f'/vendor/orders/{order_id}?error={quote(str(exc))}')
        return request.redirect(f'/vendor/orders/{order_id}')
