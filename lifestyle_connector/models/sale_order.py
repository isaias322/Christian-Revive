# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

STAGE_LABELS = {
    'order_placed': 'Order Placed',
    'processing': 'Processing',
    'packing': 'Packing',
    'out_for_delivery': 'Out for Delivery',
    'ready_for_pickup': 'Ready for Pickup',
    'delivered': 'Delivered',
    'picked_up': 'Picked Up',
    'cancelled': 'Cancelled',
}

DELIVERY_STAGE_SEQUENCE = ['order_placed', 'processing', 'packing', 'out_for_delivery', 'delivered']
PICKUP_STAGE_SEQUENCE = ['order_placed', 'processing', 'packing', 'ready_for_pickup', 'picked_up']


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'lifestyle.fcm.mixin']

    fulfillment_type = fields.Selection([
        ('delivery', 'Home Delivery'),
        ('pickup', 'In-Store Pickup'),
    ], string='Fulfillment', default='delivery', required=True)

    delivery_stage = fields.Selection(
        list(STAGE_LABELS.items()),
        string='Delivery Stage',
        default='order_placed',
        copy=False,
        tracking=True,
    )
    lifestyle_progress_percent = fields.Integer(
        string='Furniture Progress (%)',
        default=0,
        copy=False,
        tracking=True,
        help='Customer-facing build progress shown in the Revive Lifestyle app.',
    )

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.delivery_stage == 'order_placed':
                order._lifestyle_advance_stage('processing', push=False)
        return res

    def _lifestyle_product_summary(self):
        self.ensure_one()
        names = self.order_line.mapped('product_id.name')
        if not names:
            return ''
        if len(names) <= 2:
            return ', '.join(names)
        return f'{names[0]}, {names[1]} and {len(names) - 2} more'

    def _lifestyle_advance_stage(self, new_stage, push=True):
        self.ensure_one()
        if self.delivery_stage == new_stage:
            return
        self.delivery_stage = new_stage
        stage_progress = {
            'order_placed': 0,
            'processing': 15,
            'packing': 50,
            'ready_for_pickup': 85,
            'out_for_delivery': 85,
            'picked_up': 100,
            'delivered': 100,
        }
        self.lifestyle_progress_percent = max(self.lifestyle_progress_percent or 0, stage_progress.get(new_stage, 0))
        label = STAGE_LABELS.get(new_stage, new_stage)
        self.message_post(body=f'Order status updated: <b>{label}</b>')
        if push and self.partner_id:
            products = self._lifestyle_product_summary()
            body = f'Your order ({products}) is now: {label}' if products else f'Your order is now: {label}'
            self._lifestyle_send_push_to_partner(
                self.partner_id,
                title=f'Order {self.name}',
                body=body,
                data={'type': 'order_status', 'order_id': self.id, 'stage': new_stage},
            )

    def action_mark_packing(self):
        for order in self:
            order._lifestyle_advance_stage('packing')

    def action_notify_ready_for_pickup(self):
        for order in self:
            order._lifestyle_advance_stage('ready_for_pickup')

    def action_notify_out_for_delivery(self):
        for order in self:
            order._lifestyle_advance_stage('out_for_delivery')

    def action_mark_delivered(self):
        for order in self:
            order._lifestyle_advance_stage('delivered')

    def action_mark_picked_up(self):
        for order in self:
            order._lifestyle_advance_stage('picked_up')

    def _lifestyle_media_attachments(self):
        self.ensure_one()
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.id),
            '|',
            ('mimetype', 'like', 'image/'),
            ('mimetype', 'like', 'video/'),
        ], order='create_date desc')

    def _lifestyle_latest_media_attachment(self):
        self.ensure_one()
        return self._lifestyle_media_attachments()[:1]

    def _lifestyle_latest_photo_attachment(self):
        self.ensure_one()
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.id),
            ('mimetype', 'like', 'image/'),
        ], order='create_date desc', limit=1)

    def _lifestyle_attachment_url(self, attachment):
        if not attachment:
            return False
        token = self.env['lifestyle.attachment.token'].grant(attachment)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f'{base_url}/lifestyle/api/image/attachment/{attachment.id}/{token.token}'

    def _lifestyle_photo_url(self):
        self.ensure_one()
        return self._lifestyle_attachment_url(self._lifestyle_latest_photo_attachment())

    def _lifestyle_media_url(self):
        self.ensure_one()
        return self._lifestyle_attachment_url(self._lifestyle_latest_media_attachment())

    def _lifestyle_media_mimetype(self):
        self.ensure_one()
        attachment = self._lifestyle_latest_media_attachment()
        return attachment.mimetype if attachment else False

    def _lifestyle_media_list(self):
        self.ensure_one()
        return [{
            'url': self._lifestyle_attachment_url(attachment),
            'mimetype': attachment.mimetype,
        } for attachment in self._lifestyle_media_attachments()]

    def action_send_media_update(self, new_count=1):
        self.ensure_one()
        customer = self.partner_id
        if not customer:
            raise UserError('This order has no customer to notify.')

        attachment = self._lifestyle_latest_media_attachment()
        if not attachment:
            raise UserError(
                'No photo or video found on this order yet.\n\n'
                'Upload a furniture progress photo or video first, then send it to the customer.'
            )

        media_url = self._lifestyle_attachment_url(attachment)
        is_video = (attachment.mimetype or '').startswith('video/')
        products = self._lifestyle_product_summary()
        if new_count > 1:
            title = f'{new_count} new updates on your {products}' if products else f'{new_count} new updates on order {self.name}'
        else:
            media_label = 'video' if is_video else 'photo'
            title = f'A {media_label} of your {products}' if products else f'A {media_label} from your order {self.name}'

        sent = self._lifestyle_send_push_to_partner(
            customer,
            title=title,
            body=f'Your furniture is {self.lifestyle_progress_percent or 0}% complete.',
            data={
                'type': 'order_media',
                'order_id': self.id,
                'partner_id': customer.id,
                'media_type': 'video' if is_video else 'image',
            },
            image_url=False if is_video else media_url,
        )
        if not sent:
            raise UserError('Media attached, but the customer has no registered device to notify yet.')

        self.with_context(mail_create_nosubscribe=True, mail_notify_force_send=False).message_post(
            body=f'Furniture progress update sent only to customer: {customer.display_name}.',
            subtype_xmlid='mail.mt_note',
        )

    def action_send_photo_to_customer(self):
        self.ensure_one()
        self.action_send_media_update(new_count=1)
