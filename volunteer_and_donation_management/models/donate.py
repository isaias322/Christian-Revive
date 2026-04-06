from odoo import fields, models, api

class Donate(models.Model):
    _name = 'donate'
    _description = 'Donation Type'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    image = fields.Binary(string='Image')
    goal_amount = fields.Float(string='Goal Amount', default=0)
    raised_amount = fields.Float(string='Raised Amount', default=0, readonly=True)
    donation_count = fields.Integer(string='Number of Donations', default=0, readonly=True)
    is_active = fields.Boolean(string='Active', default=True)
    currency_symbol = fields.Char(string='Currency Symbol', default='Rs')

    # Multiple images
    image_2 = fields.Binary(string='Image 2')
    image_3 = fields.Binary(string='Image 3')
    
    # Project PDF
    project_pdf = fields.Binary(string='Project PDF')
    project_pdf_filename = fields.Char(string='PDF Filename')

    transaction_ids = fields.One2many('donation.transaction', 'donate_id', string='Transactions')

    def action_record_donation(self, amount, donor_name='', donor_email='', donor_phone='', partner_id=False):
        """Called from Flutter to record a donation and create a sale order"""
        self.ensure_one()

        # Create transaction
        self.env['donation.transaction'].create({
            'donate_id': self.id,
            'amount': amount,
            'donor_name': donor_name,
            'donor_email': donor_email,
            'donor_phone': donor_phone,
            'partner_id': partner_id or False,
        })

        # Update totals
        self.sudo().write({
            'raised_amount': self.raised_amount + amount,
            'donation_count': self.donation_count + 1,
        })

        # Create sale order
        so_partner_id = partner_id
        if not so_partner_id:
            # If no partner, find or create one
            if donor_email:
                existing = self.env['res.partner'].sudo().search(
                    [('email', '=', donor_email)], limit=1)
                if existing:
                    so_partner_id = existing.id
            if not so_partner_id and donor_name:
                new_partner = self.env['res.partner'].sudo().create({
                    'name': donor_name or 'Anonymous Donor',
                    'email': donor_email or False,
                    'phone': donor_phone or False,
                })
                so_partner_id = new_partner.id
            if not so_partner_id:
                # Use default public partner
                so_partner_id = self.env.ref('base.public_partner').id

        # Find or create a donation product
        product = self.env['product.product'].sudo().search(
            [('name', '=', 'Donation - %s' % self.name)], limit=1)
        if not product:
            product = self.env['product.product'].sudo().create({
                'name': 'Donation - %s' % self.name,
                'type': 'service',
                'list_price': 0,
                'sale_ok': True,
                'purchase_ok': False,
            })

        # Create the sale order
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': so_partner_id,
            'note': 'Donation for: %s' % self.name,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': 'Donation - %s' % self.name,
                'product_uom_qty': 1,
                'price_unit': amount,
            })],
        })
    
        # Auto-confirm the sale order
        sale_order.sudo().action_confirm()

        return {
            'success': True,
            'new_raised': self.raised_amount,
            'new_count': self.donation_count,
            'sale_order_id': sale_order.id,
            'sale_order_name': sale_order.name,
        }


class DonationTransaction(models.Model):
    _name = 'donation.transaction'
    _description = 'Donation Transaction'
    _order = 'create_date desc'

    donate_id = fields.Many2one('donate', string='Donation Type', required=True, ondelete='cascade')
    amount = fields.Float(string='Amount', required=True)
    donor_name = fields.Char(string='Donor Name')
    donor_email = fields.Char(string='Donor Email')
    donor_phone = fields.Char(string='Donor Phone')
    partner_id = fields.Many2one('res.partner', string='Contact')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='confirmed')