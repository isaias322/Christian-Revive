from odoo import fields, models, api

class ProductTemplateStore(models.Model):
    _inherit = 'product.template'

    is_store_product = fields.Boolean(string='Show in App Store', default=False)
    compare_price = fields.Float(string='Compare at Price')
    color_options = fields.Char(string='Color Options', help='Comma separated: Royal Brown,Silver,Teal,Black')
    size_options = fields.Char(string='Size Options', help='Comma separated: 6,8,10,14,18,20')
    store_rating = fields.Float(string='Rating', default=0)
    store_review_count = fields.Integer(string='Review Count', default=0)
    store_sold_count = fields.Integer(string='Sold Count', default=0)
    store_description = fields.Text(string='Store Description')
    store_image_2 = fields.Binary(string='Store Image 2')
    store_image_3 = fields.Binary(string='Store Image 3')
    store_image_4 = fields.Binary(string='Store Image 4')
    store_sequence = fields.Integer(string='Store Sequence', default=10)