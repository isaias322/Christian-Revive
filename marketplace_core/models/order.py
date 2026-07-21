# -*- coding: utf-8 -*-
import base64
import io

import qrcode
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from odoo import api, fields, models, _
from odoo.exceptions import UserError

LABEL_SIZE = (100 * mm, 150 * mm)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_marketplace_order = fields.Boolean(
        string='Marketplace Order', default=False, index=True)
    marketplace_seller_id = fields.Many2one(
        'marketplace.seller', string='Seller Shop', index=True)
    marketplace_payment_method = fields.Selection([
        ('cod', 'Cash on Delivery'),
        ('jazzcash', 'JazzCash'),
        ('easypaisa', 'EasyPaisa'),
        ('card', 'Card'),
        ('bank', 'Bank Transfer'),
    ], string='Payment Method')
    payment_received = fields.Boolean(
        string='Payment Received', tracking=True,
        help='For prepaid methods: money confirmed in the platform account. '
             'For COD: cash collected by the courier and reconciled.')

    # ------------------------------------------------------------------
    # Escrow
    # ------------------------------------------------------------------
    escrow_state = fields.Selection([
        ('none', 'No Escrow'),
        ('held', 'Funds Held'),
        ('released', 'Released to Seller'),
        ('refunded', 'Refunded to Buyer'),
    ], default='none', tracking=True, index=True, copy=False)
    escrow_release_date = fields.Datetime(copy=False)

    # ------------------------------------------------------------------
    # Delivery / logistics
    # ------------------------------------------------------------------
    marketplace_delivery_state = fields.Selection([
        ('pending', 'Preparing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    ], default='pending', tracking=True, copy=False)
    marketplace_courier_id = fields.Many2one(
        'marketplace.courier', string='Courier')
    tracking_number = fields.Char(copy=False)
    tracking_url = fields.Char(compute='_compute_tracking_url')
    shipping_label_ref = fields.Char(
        string='Shipping Label Ref', copy=False,
        help='Reference of the prepaid label booked with the courier.')
    shipped_date = fields.Datetime(copy=False)
    delivered_date = fields.Datetime(copy=False)
    buyer_confirmed_delivery = fields.Boolean(copy=False, tracking=True)

    # ------------------------------------------------------------------
    # Money split
    # ------------------------------------------------------------------
    marketplace_item_total = fields.Monetary(
        compute='_compute_marketplace_amounts', store=True,
        string='Items Total')
    buyer_protection_fee = fields.Monetary(
        compute='_compute_marketplace_amounts', store=True)
    shipping_fee = fields.Monetary(
        compute='_compute_marketplace_amounts', store=True)
    platform_commission = fields.Monetary(
        compute='_compute_marketplace_amounts', store=True)
    seller_payout_amount = fields.Monetary(
        compute='_compute_marketplace_amounts', store=True,
        help='Amount credited to the seller wallet when escrow is released.')

    dispute_ids = fields.One2many('marketplace.dispute', 'order_id')
    dispute_count = fields.Integer(compute='_compute_dispute_count')
    review_ids = fields.One2many('marketplace.review', 'order_id')

    @api.depends('order_line.price_total', 'order_line.product_id',
                 'marketplace_seller_id')
    def _compute_marketplace_amounts(self):
        fee_product = self.env.ref(
            'marketplace_core.product_buyer_protection_fee',
            raise_if_not_found=False)
        ship_product = self.env.ref(
            'marketplace_core.product_shipping_fee',
            raise_if_not_found=False)
        for order in self:
            if not order.is_marketplace_order:
                order.marketplace_item_total = 0.0
                order.buyer_protection_fee = 0.0
                order.shipping_fee = 0.0
                order.platform_commission = 0.0
                order.seller_payout_amount = 0.0
                continue
            fee_lines = order.order_line.filtered(
                lambda l: fee_product and
                l.product_id.product_tmpl_id == fee_product)
            ship_lines = order.order_line.filtered(
                lambda l: ship_product and
                l.product_id.product_tmpl_id == ship_product)
            item_lines = order.order_line - fee_lines - ship_lines
            order.marketplace_item_total = sum(item_lines.mapped('price_total'))
            order.buyer_protection_fee = sum(fee_lines.mapped('price_total'))
            order.shipping_fee = sum(ship_lines.mapped('price_total'))
            commission_pct = (
                order.marketplace_seller_id._effective_commission_pct()
                if order.marketplace_seller_id else 0.0)
            order.platform_commission = (
                order.marketplace_item_total * commission_pct / 100.0)
            order.seller_payout_amount = (
                order.marketplace_item_total - order.platform_commission)

    def _compute_tracking_url(self):
        for order in self:
            order.tracking_url = (
                order.marketplace_courier_id.get_tracking_url(
                    order.tracking_number)
                if order.marketplace_courier_id and order.tracking_number
                else False)

    def _compute_dispute_count(self):
        for order in self:
            order.dispute_count = len(order.dispute_ids)

    # ------------------------------------------------------------------
    # Fee engine
    # ------------------------------------------------------------------
    def _add_marketplace_fees(self, courier=None):
        """Append buyer-protection and shipping fee lines."""
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        fixed = float(icp.get_param(
            'marketplace_core.buyer_protection_fixed', '100.0'))
        pct = float(icp.get_param(
            'marketplace_core.buyer_protection_pct', '5.0'))
        items_total = sum(
            self.order_line.mapped('price_unit'))
        fee = fixed + items_total * pct / 100.0

        lines = []
        fee_product = self.env.ref(
            'marketplace_core.product_buyer_protection_fee')
        lines.append((0, 0, {
            'product_id': fee_product.product_variant_id.id,
            'product_uom_qty': 1,
            'price_unit': fee,
        }))
        if courier and courier.flat_rate:
            ship_product = self.env.ref(
                'marketplace_core.product_shipping_fee')
            lines.append((0, 0, {
                'product_id': ship_product.product_variant_id.id,
                'product_uom_qty': 1,
                'price_unit': courier.flat_rate,
            }))
        self.write({'order_line': lines})

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def action_confirm_marketplace(self):
        """Confirm the order, reserve listings and open escrow."""
        for order in self:
            order.action_confirm()
            order.escrow_state = 'held'
            listings = order._get_marketplace_listings()
            listings.action_mark_reserved()
            order.message_post(body=_(
                'Marketplace order placed. Funds held in escrow until the '
                'buyer confirms delivery.'))
        return True

    def _get_marketplace_listings(self):
        fee_refs = [
            'marketplace_core.product_buyer_protection_fee',
            'marketplace_core.product_shipping_fee',
        ]
        fee_templates = self.env['product.template'].browse()
        for ref in fee_refs:
            rec = self.env.ref(ref, raise_if_not_found=False)
            if rec:
                fee_templates |= rec
        return (self.order_line.mapped('product_id.product_tmpl_id')
                - fee_templates)

    def action_mark_shipped(self, tracking_number=None, courier_id=None):
        for order in self:
            if not order.is_marketplace_order:
                continue
            if order.marketplace_delivery_state != 'pending':
                raise UserError(_('Order %s is already shipped.') % order.name)
            vals = {
                'marketplace_delivery_state': 'shipped',
                'shipped_date': fields.Datetime.now(),
            }
            if tracking_number:
                vals['tracking_number'] = tracking_number
            if courier_id:
                vals['marketplace_courier_id'] = int(courier_id)
            order.write(vals)
            order.message_post(body=_(
                'Shipped via %(courier)s. Tracking: %(tracking)s',
                courier=order.marketplace_courier_id.name or _('courier'),
                tracking=order.tracking_number or '-'))
            if order.marketplace_courier_id and not order.shipping_label_ref:
                order.action_generate_label()
        return True

    def action_generate_label(self):
        """Generate a real, printable 4x6" prepaid shipping label (PDF,
        with a genuinely scannable QR code carrying the tracking number)
        and attach it to the order.

        This does not call a live courier API — TCS / Leopards / M&P /
        BlueEx all require a signed merchant agreement and real API
        credentials neither this build nor a fresh marketplace has yet.
        What it produces instead is the actual label artifact a seller
        needs to hand the parcel to a rider: sender/recipient blocks, the
        order reference, a COD-amount callout when relevant, and a QR
        code — the same shape of document a live integration would return,
        just generated locally instead of fetched from a courier's API.
        Swapping in a real courier means calling their booking endpoint
        here and using the label file it returns instead of this one.
        """
        Attachment = self.env['ir.attachment'].sudo()
        for order in self:
            if not order.marketplace_courier_id:
                raise UserError(_('Select a courier first.'))
            if not order.tracking_number:
                order.tracking_number = self.env['ir.sequence'].sudo(
                    ).next_by_code('marketplace.shipping.label')
            if not order.shipping_label_ref:
                order.shipping_label_ref = order.tracking_number
            pdf = order._generate_label_pdf()
            attachment = Attachment.search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id),
                ('name', '=', 'shipping-label-%s.pdf' % order.name),
            ], limit=1)
            vals = {
                'name': 'shipping-label-%s.pdf' % order.name,
                'datas': base64.b64encode(pdf),
                'res_model': 'sale.order',
                'res_id': order.id,
                'mimetype': 'application/pdf',
            }
            if attachment:
                attachment.write(vals)
            else:
                attachment = Attachment.create(vals)
            order.message_post(body=_(
                'Prepaid shipping label generated: %s') % order.shipping_label_ref,
                attachment_ids=[attachment.id])
        return True

    def _generate_label_pdf(self):
        """Render a 100x150mm prepaid label. Returns raw PDF bytes."""
        self.ensure_one()
        order = self
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=LABEL_SIZE)
        w, h = LABEL_SIZE
        margin = 4 * mm

        # Header band: courier name + PREPAID badge
        c.setFillColorRGB(0.05, 0.58, 0.53)
        c.rect(0, h - 14 * mm, w, 14 * mm, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont('Helvetica-Bold', 14)
        c.drawString(margin, h - 10 * mm,
                     (order.marketplace_courier_id.name or 'COURIER').upper())
        c.setFont('Helvetica-Bold', 9)
        c.drawRightString(w - margin, h - 10 * mm, 'PREPAID')

        y = h - 20 * mm
        c.setFillColorRGB(0, 0, 0)

        def block(title, lines, y0):
            c.setFont('Helvetica-Bold', 7.5)
            c.drawString(margin, y0, title)
            c.setFont('Helvetica', 8.5)
            yy = y0 - 4.2 * mm
            for line in lines:
                c.drawString(margin, yy, line[:48])
                yy -= 4.0 * mm
            return yy

        seller = order.marketplace_seller_id
        y = block('FROM', [
            seller.name or '',
            seller.city or '',
        ], y)
        y -= 2 * mm
        c.line(margin, y, w - margin, y)
        y -= 5 * mm

        partner = order.partner_id
        y = block('DELIVER TO', [
            partner.name or '',
            partner.street or '',
            '%s %s' % (partner.city or '', partner.zip or ''),
            partner.phone or '',
        ], y)
        y -= 2 * mm
        c.line(margin, y, w - margin, y)
        y -= 6 * mm

        c.setFont('Helvetica-Bold', 9)
        c.drawString(margin, y, 'ORDER %s' % order.name)
        y -= 6 * mm
        c.setFont('Helvetica-Bold', 11)
        c.drawString(margin, y, 'TRACKING %s' % (order.tracking_number or ''))
        y -= 8 * mm

        if order.marketplace_payment_method == 'cod':
            c.setFillColorRGB(0.98, 0.75, 0.15)
            c.rect(margin, y - 9 * mm, w - 2 * margin, 9 * mm, fill=1,
                   stroke=0)
            c.setFillColorRGB(0, 0, 0)
            c.setFont('Helvetica-Bold', 10)
            c.drawCentredString(
                w / 2, y - 6 * mm,
                'COLLECT COD: %s %.0f' % (
                    order.currency_id.symbol or '', order.amount_total))
            y -= 12 * mm

        # QR code carrying the tracking number, bottom-right
        qr_img = qrcode.make(order.tracking_number or order.name)
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format='PNG')
        qr_buf.seek(0)
        from reportlab.lib.utils import ImageReader
        qr_size = 24 * mm
        c.drawImage(ImageReader(qr_buf), w - margin - qr_size, margin,
                    width=qr_size, height=qr_size)
        c.setFont('Helvetica', 6.5)
        c.drawString(margin, margin + 2 * mm,
                     'Items: %d' % len(order._get_marketplace_listings()))

        c.showPage()
        c.save()
        return buf.getvalue()

    def action_mark_delivered(self):
        for order in self:
            order.write({
                'marketplace_delivery_state': 'delivered',
                'delivered_date': fields.Datetime.now(),
            })
        return True

    def action_confirm_delivery(self):
        """Buyer confirms receipt -> release escrow to seller wallet."""
        for order in self:
            if order.escrow_state != 'held':
                raise UserError(_(
                    'Escrow is not held on order %s.') % order.name)
            order.write({
                'buyer_confirmed_delivery': True,
                'marketplace_delivery_state': 'delivered',
                'delivered_date': order.delivered_date or fields.Datetime.now(),
            })
            order.action_release_escrow()
        return True

    def action_release_escrow(self):
        for order in self:
            if order.escrow_state != 'held':
                raise UserError(_(
                    'Escrow is not held on order %s.') % order.name)
            if order.dispute_ids.filtered(
                    lambda d: d.state in ('open', 'under_review')):
                raise UserError(_(
                    'Order %s has an open dispute; resolve it first.'
                ) % order.name)
            order.escrow_state = 'released'
            order.escrow_release_date = fields.Datetime.now()
            self.env['marketplace.wallet.transaction'].sudo().create({
                'seller_id': order.marketplace_seller_id.id,
                'order_id': order.id,
                'transaction_type': 'sale_credit',
                'amount': order.seller_payout_amount,
                'state': 'done',
                'note': _('Escrow released for order %s') % order.name,
            })
            order._get_marketplace_listings().action_mark_sold()
            order.message_post(body=_(
                'Escrow released: %(amount).2f credited to seller wallet.',
                amount=order.seller_payout_amount))
        return True

    def action_refund_escrow(self):
        for order in self:
            if order.escrow_state != 'held':
                raise UserError(_(
                    'Escrow is not held on order %s.') % order.name)
            order.escrow_state = 'refunded'
            for listing in order._get_marketplace_listings():
                # Each listing here represents exactly one unit bought
                # by this order (cart only allows one unit of a given
                # listing per buyer), so put that unit back in stock —
                # regardless of whether it's the state that used up the
                # last unit (-> 'reserved') or a different unit already
                # sold this listing out entirely in the meantime
                # (-> 'sold').
                listing.stock_quantity += 1
                if listing.listing_state in ('reserved', 'sold', 'removed'):
                    listing.write(
                        {'listing_state': 'active', 'is_published': True})
            order.message_post(body=_(
                'Escrow refunded to buyer. Listing re-activated.'))
        return True

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_auto_release_escrow(self):
        """Release escrow N days after delivery if the buyer stays silent
        and no dispute was opened (standard marketplace behaviour)."""
        icp = self.env['ir.config_parameter'].sudo()
        days = int(icp.get_param(
            'marketplace_core.escrow_auto_release_days', '3'))
        deadline = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        orders = self.search([
            ('is_marketplace_order', '=', True),
            ('escrow_state', '=', 'held'),
            ('marketplace_delivery_state', '=', 'delivered'),
            ('delivered_date', '<=', deadline),
        ])
        for order in orders:
            if order.dispute_ids.filtered(
                    lambda d: d.state in ('open', 'under_review')):
                continue
            order.action_release_escrow()
