# -*- coding: utf-8 -*-
from odoo import fields, models


class ReviveHomepageSection(models.Model):
    _name = 'lifestyle.homepage.section'
    _description = 'Revive Website Homepage Section'
    _order = 'sequence, id'

    name = fields.Char(string='Internal Name', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    section_key = fields.Selection([
        ('featured', 'Featured Products'),
        ('process', 'Order Process'),
        ('cta', 'Call To Action'),
        ('content', 'Custom Content'),
        ('header', 'Header Section'),
        ('footer', 'Footer Section'),
    ], string='Homepage Area', required=True, default='featured')
    placement = fields.Selection([
        ('before_hero', 'Before Hero Slider'),
        ('main', 'Main Content'),
        ('before_footer', 'Before Footer'),
    ], string='Page Position', required=True, default='main',
       help='Choose where this standalone homepage section should appear.')

    kicker = fields.Char(string='Small Heading')
    title = fields.Char(string='Title', required=True)
    subtitle = fields.Text(string='Description')
    image = fields.Binary(string='Section Image')

    button_label = fields.Char(string='Button Label')
    button_url = fields.Char(string='Button URL')
    button_icon = fields.Char(string='Button Icon', default='fa-arrow-right')

    product_limit = fields.Integer(string='Featured Product Count', default=4)
    empty_title = fields.Char(string='Empty Products Message', default='Products will appear here when you publish them for Revive Lifestyle.')
    empty_button_label = fields.Char(string='Empty Button Label', default='Go to Shop')
    empty_button_url = fields.Char(string='Empty Button URL', default='/shop')

    background_style = fields.Selection([
        ('default', 'Default'),
        ('light', 'Warm Light'),
        ('sage', 'Sage'),
        ('cream', 'Cream'),
        ('charcoal', 'Charcoal'),
        ('custom', 'Custom Colors'),
    ], string='Background Style', default='default')
    background_color = fields.Char(string='Custom Background Color', default='#FFFDF9')
    background_color_2 = fields.Char(string='Custom Second Color', default='#F7F5F0')
    text_color = fields.Char(string='Text Color')
    accent_color = fields.Char(string='Accent Color')
    card_background_color = fields.Char(string='Card Background Color')

    layout = fields.Selection([
        ('split', 'Text Left, Items Right'),
        ('reverse', 'Items Left, Text Right'),
        ('center', 'Centered'),
    ], string='Layout', default='split')
    show_button = fields.Boolean(string='Show Button', default=True)
    show_items = fields.Boolean(string='Show Cards/Chips', default=True)
    show_products = fields.Boolean(string='Show Products', default=True)
    show_status_badge = fields.Boolean(string='Show Product Status Badge', default=True)

    item_ids = fields.One2many('lifestyle.homepage.section.item', 'section_id', string='Cards and Chips')


class ReviveHomepageSectionItem(models.Model):
    _name = 'lifestyle.homepage.section.item'
    _description = 'Revive Website Homepage Section Item'
    _order = 'sequence, id'

    section_id = fields.Many2one('lifestyle.homepage.section', string='Homepage Section', required=True, ondelete='cascade')
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    icon = fields.Char(string='Icon', default='fa-check')
    title = fields.Char(string='Title', required=True)
    text = fields.Text(string='Text')
    image = fields.Binary(string='Image')
    url = fields.Char(string='Link URL')
    color = fields.Char(string='Icon/Text Color')
    background_color = fields.Char(string='Card Background Color')
    item_style = fields.Selection([
        ('card', 'Card'),
        ('chip', 'Chip'),
        ('image', 'Image Card'),
    ], string='Display Style', default='card')