# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import html_escape

STAGE_LABELS = {
    'order_placed': 'Order Placed',
    'processing': 'Build Started',
    'packing': 'Build & Packing',
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

    lifestyle_coupon_code = fields.Char(
        string='App Coupon Code Used',
        copy=False,
        help='The Promotions/Loyalty coupon code (if any) the customer applied to this order in the app.',
    )

    lifestyle_vendor_id = fields.Many2one(
        'hr.employee',
        string='Assigned Vendor',
        copy=False,
        tracking=True,
        domain="[('staff_role', '=', 'carpenter'), ('is_app_active', '=', True)]",
        help='Vendor/carpenter responsible for this furniture order in the Revive Lifestyle vendor app.',
    )
    lifestyle_stage_unlocked = fields.Boolean(
        string='Stage Correction Unlocked',
        default=False,
        copy=False,
        help=(
            'When enabled, the vendor app is allowed to move this order back to an '
            'earlier delivery stage once (e.g. to undo an accidental "Delivered" tap). '
            'Automatically turns back off after that one correction.'
        ),
    )



    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.delivery_stage == 'order_placed':
                initial_stage = 'packing' if order._lifestyle_skip_processing() else 'processing'
                order._lifestyle_advance_stage(initial_stage, push=False)
        return res

    def _lifestyle_skip_processing(self):
        """True when every line on this order is a Fruits & Vegetables
        product - those just get packed and shipped, so there's no separate
        build/processing step the way there is for furniture."""
        self.ensure_one()
        fruit_category = self.env.ref('lifestyle_connector.category_fruits_veg', raise_if_not_found=False)
        if not fruit_category:
            return False
        categ_ids = self.order_line.mapped('product_id.categ_id.id')
        if not categ_ids:
            return False
        fruit_descendant_ids = self.env['product.category'].search([
            ('id', 'child_of', fruit_category.id),
        ]).ids
        return all(categ_id in fruit_descendant_ids for categ_id in categ_ids)

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
        sequence = PICKUP_STAGE_SEQUENCE if self.fulfillment_type == 'pickup' else DELIVERY_STAGE_SEQUENCE
        if self.delivery_stage in sequence and new_stage in sequence:
            current_index = sequence.index(self.delivery_stage)
            new_index = sequence.index(new_stage)
            if new_index < current_index:
                if not self.lifestyle_stage_unlocked:
                    raise UserError(
                        'This order is already past that stage, so the vendor app can\'t move it back.\n\n'
                        'If this was set by mistake, click "Allow Stage Correction" on this order in Odoo, '
                        'then try again from the app.'
                    )
                self.lifestyle_stage_unlocked = False
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
        if push:
            self._lifestyle_send_stage_notification()


    def _lifestyle_notify_assigned_vendor(self, raise_if_no_device=True):
        self.ensure_one()
        if not self.lifestyle_vendor_id:
            if raise_if_no_device:
                raise UserError('Assign a vendor before sending the work notification.')
            return 0
        products = self._lifestyle_product_summary()
        body = f'New furniture job assigned: {products}' if products else f'New furniture job assigned: {self.name}'
        try:
            sent = self._lifestyle_send_push_to_employee(
                self.lifestyle_vendor_id,
                title=f'New job {self.name}',
                body=body,
                data={'type': 'vendor_assignment', 'order_id': self.id},
            )
        except UserError as exc:
            if raise_if_no_device:
                raise
            self.with_context(mail_create_nosubscribe=True, mail_notify_force_send=False).message_post(
                body=f'Assigned vendor notification was not sent: {html_escape(str(exc))}',
                subtype_xmlid='mail.mt_note',
            )
            return 0
        if not sent:
            message = f'Assigned vendor {self.lifestyle_vendor_id.name} has no registered vendor app device yet.'
            self.with_context(mail_create_nosubscribe=True, mail_notify_force_send=False).message_post(
                body=message,
                subtype_xmlid='mail.mt_note',
            )
            if raise_if_no_device:
                raise UserError(message)
            return 0
        self.with_context(mail_create_nosubscribe=True, mail_notify_force_send=False).message_post(
            body=f'Work notification sent to assigned vendor: {html_escape(self.lifestyle_vendor_id.name)}.',
            subtype_xmlid='mail.mt_note',
        )
        return sent

    def action_notify_assigned_vendor(self):
        for order in self:
            order._lifestyle_notify_assigned_vendor(raise_if_no_device=True)

    def _lifestyle_send_stage_notification(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError('This order has no customer to notify.')
        label = STAGE_LABELS.get(self.delivery_stage, self.delivery_stage)
        products = self._lifestyle_product_summary()
        body = f'Your furniture order ({products}) is now: {label}' if products else f'Your furniture order is now: {label}'
        sent = self._lifestyle_send_push_to_partner(
            self.partner_id,
            title=f'Order {self.name}',
            body=body,
            data={'type': 'order_status', 'order_id': self.id, 'stage': self.delivery_stage},
        )
        if not sent:
            raise UserError('Stage updated, but the customer has no registered device to notify yet.')
        self.with_context(mail_create_nosubscribe=True, mail_notify_force_send=False).message_post(
            body=f'Stage notification sent only to customer: {self.partner_id.display_name}.',
            subtype_xmlid='mail.mt_note',
        )

    def action_unlock_stage_correction(self):
        for order in self:
            order.lifestyle_stage_unlocked = True
            order.message_post(body='Stage correction unlocked - the vendor app may move this order back one stage.')

    def action_lock_stage_correction(self):
        for order in self:
            order.lifestyle_stage_unlocked = False

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
            '|', '|',
            ('mimetype', 'like', 'image/'),
            ('mimetype', 'like', 'video/'),
            ('mimetype', '=', 'text/plain'),
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
            'url': self._lifestyle_attachment_url(attachment) if attachment.mimetype != 'text/plain' else '',
            'mimetype': attachment.mimetype,
            'comment': attachment.description or '',
            'stage_label': attachment.lifestyle_stage_label or '',
        } for attachment in self._lifestyle_media_attachments()]

    def _lifestyle_can_send_media(self):
        """False once the order is fully delivered/picked up (or cancelled) -
        there's no furniture left in progress, so the vendor has nothing new
        to show the customer and shouldn't be able to send further updates."""
        self.ensure_one()
        return self.delivery_stage not in ('delivered', 'picked_up') and self.state != 'cancel'

    def action_send_media_update(self, new_count=1, comment=None):
        self.ensure_one()
        if not self._lifestyle_can_send_media():
            raise UserError('This order has already been completed - no further updates can be sent.')

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
        is_comment_only = attachment.mimetype == 'text/plain'
        products = self._lifestyle_product_summary()
        if is_comment_only:
            title = f'A workshop note about your {products}' if products else f'A workshop note about order {self.name}'
        elif new_count > 1:
            title = f'{new_count} new updates on your {products}' if products else f'{new_count} new updates on order {self.name}'
        else:
            media_label = 'video' if is_video else 'photo'
            title = f'A {media_label} of your {products}' if products else f'A {media_label} from your order {self.name}'

        sent = self._lifestyle_send_push_to_partner(
            customer,
            title=title,
            body=(comment or f'Your furniture is {self.lifestyle_progress_percent or 0}% complete.'),
            data={
                'type': 'order_media',
                'order_id': self.id,
                'partner_id': customer.id,
                'media_type': 'comment' if is_comment_only else ('video' if is_video else 'image'),
            },
            image_url=False if is_video or is_comment_only else media_url,
        )
        if not sent:
            raise UserError('Media attached, but the customer has no registered device to notify yet.')

        self.with_context(mail_create_nosubscribe=True, mail_notify_force_send=False).message_post(
            body=(
                f'Furniture progress update sent only to customer: {customer.display_name}.'
                + (f'<br/><b>Comment:</b> {html_escape(comment)}' if comment else '')
            ),
            subtype_xmlid='mail.mt_note',
        )

    def action_send_photo_to_customer(self):
        self.ensure_one()
        self.action_send_media_update(new_count=1)
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lifestyle_color = fields.Char(string='Selected Color', copy=False)




