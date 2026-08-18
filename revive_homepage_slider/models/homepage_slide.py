# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ReviveHomepageSlide(models.Model):
    _name = 'lifestyle.homepage.slide'
    _description = 'Revive Website Hero Slide'
    _order = 'sequence, id'

    name = fields.Char(string='Internal Name', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    kicker = fields.Char(string='Small Heading', default='Revive Lifestyle Furniture')
    title = fields.Char(string='Main Title', required=True)
    subtitle = fields.Text(string='Description')
    image = fields.Binary(string='Hero Image')

    primary_button_label = fields.Char(string='Primary Button Label', default='Shop Furniture')
    primary_button_url = fields.Char(string='Primary Button URL', default='/shop')
    secondary_button_label = fields.Char(string='Secondary Button Label', default='Ask a Question')
    secondary_button_url = fields.Char(string='Secondary Button URL', default='/contactus')

    trust_1_icon = fields.Char(string='Trust 1 Icon', default='fa-check')
    trust_1_text = fields.Char(string='Trust 1 Text', default='Build tracking')
    trust_2_icon = fields.Char(string='Trust 2 Icon', default='fa-camera')
    trust_2_text = fields.Char(string='Trust 2 Text', default='Workshop updates')
    trust_3_icon = fields.Char(string='Trust 3 Icon', default='fa-truck')
    trust_3_text = fields.Char(string='Trust 3 Text', default='Delivery support')

    card_icon = fields.Char(string='Card Icon', default='fa-home')
    card_title = fields.Char(string='Card Title', default='Designed around your room')
    card_text = fields.Text(string='Card Text')

    badge_1_value = fields.Char(string='Badge 1 Value', default='50%')
    badge_1_label = fields.Char(string='Badge 1 Label', default='Build progress')
    badge_2_icon = fields.Char(string='Badge 2 Icon', default='fa-bell')
    badge_2_label = fields.Char(string='Badge 2 Label', default='Vendor updates')

    background_style = fields.Selection([
        ('charcoal', 'Charcoal Green'),
        ('sage', 'Sage Green'),
        ('olive', 'Olive'),
        ('warm', 'Warm Wood'),
        ('walnut', 'Walnut Brown'),
        ('midnight', 'Midnight'),
        ('cream', 'Cream Light'),
        ('terracotta', 'Terracotta'),
        ('custom', 'Custom Colors'),
    ], string='Background Style', default='charcoal')
    background_color = fields.Char(
        string='Custom Background Color',
        default='#252821',
        help='Use a hex color like #2E2E2A. Used when Background Style is Custom Colors.',
    )
    background_color_2 = fields.Char(
        string='Custom Second Color',
        default='#5C7050',
        help='Optional second hex color for the gradient, like #5C7050.',
    )
    text_color = fields.Char(
        string='Text Color',
        help='Optional hex color for the slide text. Leave empty for automatic white/dark text.',
    )
    accent_color = fields.Char(
        string='Accent Color',
        help='Optional hex color for highlights, dots, and small decorative lines.',
    )
    overlay_opacity = fields.Selection([
        ('0.35', 'Light'),
        ('0.55', 'Medium'),
        ('0.72', 'Strong'),
        ('0.86', 'Very Strong'),
    ], string='Image Overlay', default='0.72')
    text_alignment = fields.Selection([
        ('left', 'Left'),
        ('center', 'Center'),
    ], string='Text Alignment', default='left')
    content_layout = fields.Selection([
        ('split', 'Text Left, Visual Right'),
        ('reverse', 'Visual Left, Text Right'),
        ('center', 'Centered Text'),
    ], string='Slide Layout', default='split')
    hero_height = fields.Selection([
        ('compact', 'Compact'),
        ('default', 'Default'),
        ('tall', 'Tall'),
    ], string='Hero Height', default='default')
    image_fit = fields.Selection([
        ('cover', 'Cover'),
        ('contain', 'Contain'),
    ], string='Hero Image Fit', default='cover')
    button_style = fields.Selection([
        ('filled', 'Filled Primary'),
        ('outline', 'Outline Primary'),
        ('soft', 'Soft Light'),
    ], string='Button Style', default='filled')
    show_visual_card = fields.Boolean(string='Show Right Visual Card', default=True)
    show_badges = fields.Boolean(string='Show Floating Badges', default=True)
    autoplay_seconds = fields.Integer(string='Autoplay Seconds', default=5)

    @api.model
    def _rl_fix_slide_copy_for_actual_catalog(self):
        """Re-applies on every module upgrade. The seed data (noupdate="1",
        so it never updates itself) wrote all three hero slides as if
        furniture were the only thing sold - the store also carries
        cold-pressed oils and pantry staples, so every slide claimed an
        incomplete catalog. Slide 1 becomes a combined intro, slide 2 stays
        furniture-specific (a real feature, not a false "furniture only"
        claim), slide 3 becomes the pantry/natural-goods slide."""
        updates = {
            'homepage_slide_furniture': {
                'kicker': 'Revive Lifestyle',
                'title': 'Handcrafted pieces and natural pantry goods, made honestly',
                'subtitle': (
                    'Built-to-order pieces for your home, plus cold-pressed oils and '
                    'healthy pantry staples - browse everything and track your order '
                    'from first look to your door.'
                ),
                'primary_button_label': 'Shop All',
                'trust_2_icon': 'fa-leaf',
                'trust_2_text': 'Cold-pressed',
                'card_icon': 'fa-leaf',
                'card_title': 'Two kinds of care',
                'card_text': (
                    'From handcrafted furniture to cold-pressed oils - each one made '
                    'and packed with the same attention.'
                ),
            },
            'homepage_slide_updates': {
                'kicker': 'Healthy Pantry',
                'title': 'Cold-pressed oils and pantry staples, made naturally',
                'subtitle': (
                    'Small-batch cold-pressed oils, desi shakkar, and healthy pantry '
                    'staples - simple ingredients, made the honest way.'
                ),
                'primary_button_label': 'Shop Pantry',
                'secondary_button_label': 'Talk to Us',
                'trust_1_icon': 'fa-leaf',
                'trust_1_text': 'Cold-pressed',
                'trust_2_icon': 'fa-check',
                'trust_2_text': 'Small batch',
                'trust_3_icon': 'fa-truck',
                'trust_3_text': 'Fresh delivery',
                'card_icon': 'fa-leaf',
                'card_title': 'Simple, honest ingredients',
                'card_text': (
                    'No shortcuts - just cold-pressed oils and pantry staples made '
                    'the way they should be.'
                ),
                'badge_1_value': '100%',
                'badge_1_label': 'Natural',
                'badge_2_icon': 'fa-leaf',
                'badge_2_label': 'Fresh batch',
            },
        }
        for xmlid, vals in updates.items():
            slide = self.env.ref('revive_homepage_slider.%s' % xmlid, raise_if_not_found=False)
            if slide:
                slide.write(vals)
