# -*- coding: utf-8 -*-
import base64
import logging
from datetime import timedelta

from odoo import fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, Response

from ..models.sale_order import STAGE_LABELS, DELIVERY_STAGE_SEQUENCE, PICKUP_STAGE_SEQUENCE

_logger = logging.getLogger(__name__)


def _safe_error_message(exc):
    """UserError/ValidationError carry a message that's meant to be shown to
    the user, so pass those through. Anything else (a bug, a DB error, etc.)
    gets logged in full server-side but only a generic message goes to the
    app, so internals never leak to the client."""
    if isinstance(exc, (UserError, ValidationError)):
        return str(exc)
    _logger.exception('Unexpected error in lifestyle API')
    return 'Something went wrong. Please try again.'


def _current_partner():
    """Returns the logged-in partner, or None if the session is anonymous/public."""
    user = request.env.user
    if not user or user._is_public():
        return None
    return user.partner_id


def _is_staff():
    """True if the logged-in Odoo session (cookie-based) should see the app's
    Vendor Tools. This only covers full Odoo administrators - carpenters use
    a separate App Login Email + App PIN flow (see _vendor_employee) instead
    of a real Odoo account, so they never hit this check at all.
    """
    user = request.env.user
    return bool(user) and not user._is_public() and user.has_group('base.group_system')


def _vendor_employee():
    """Returns the carpenter hr.employee authorized for vendor-tools requests,
    identified by the X-Vendor-Token header issued by /lifestyle/api/vendor/login,
    or None if missing/invalid."""
    token = request.httprequest.headers.get('X-Vendor-Token')
    if not token:
        return None
    vendor_session = request.env['lifestyle.vendor.session'].sudo().search([('token', '=', token)], limit=1)
    if not vendor_session:
        return None
    employee = vendor_session.employee_id
    if not employee.is_app_active or employee.staff_role != 'carpenter':
        return None
    return employee


def _vendor_access():
    """True if this request is authorized for vendor-tools endpoints, either
    as a full Odoo admin (existing session) or a carpenter (PIN token)."""
    return _is_staff() or _vendor_employee() is not None


def _timeline_for(order):
    sequence = PICKUP_STAGE_SEQUENCE if order.fulfillment_type == 'pickup' else DELIVERY_STAGE_SEQUENCE
    if order._lifestyle_skip_processing():
        sequence = [stage for stage in sequence if stage != 'processing']
    if order.delivery_stage == 'cancelled':
        return [{'key': 'cancelled', 'label': STAGE_LABELS['cancelled'], 'done': True, 'current': True}]
    try:
        current_index = sequence.index(order.delivery_stage)
    except ValueError:
        current_index = 0
    return [
        {
            'key': key,
            'label': STAGE_LABELS[key],
            'done': idx <= current_index,
            'current': idx == current_index,
        }
        for idx, key in enumerate(sequence)
    ]


def _product_image_url(product_id):
    return f'/lifestyle/api/image/product/{product_id}'


def _store_image_url(product_id, image_number):
    return f'/lifestyle/api/image/product/{product_id}/store/{image_number}'


def _color_image_url(product_id, image_number):
    return f'/lifestyle/api/image/product/{product_id}/color/{image_number}'


def _color_row_image_url(color_image_id):
    return f'/lifestyle/api/image/product/color-row/{color_image_id}'


def _banner_image_url(banner_id):
    return f'/lifestyle/api/image/banner/{banner_id}'


def _app_visibility_domain(Product):
    if 'is_store_product' in Product._fields:
        return [('is_store_product', '=', True)]
    return [('lifestyle_app_visible', '=', True)]


def _is_app_visible(product):
    if not product.exists():
        return False
    if 'is_store_product' in product._fields:
        return bool(product.is_store_product)
    return bool(product.lifestyle_app_visible)


def _store_value(product, field_name, default=False):
    if field_name not in product._fields:
        return default
    value = getattr(product, field_name)
    return value if value is not False else default


def _product_tax_info(product):
    taxes = product.taxes_id if 'taxes_id' in product._fields else request.env['account.tax']
    if taxes:
        company = product.company_id or request.env.company
        taxes = taxes.filtered(lambda tax: not tax.company_id or tax.company_id == company)
    if not taxes:
        return {
            'tax_label': '',
            'tax_amount': 0.0,
            'price_with_tax': product.list_price,
            'tax_details': [],
        }

    variant = product.product_variant_id if product.product_variant_id else False
    tax_result = taxes.compute_all(
        product.list_price,
        currency=product.currency_id,
        quantity=1.0,
        product=variant,
        partner=False,
    )
    total_excluded = tax_result.get('total_excluded', product.list_price)
    total_included = tax_result.get('total_included', product.list_price)
    return {
        'tax_label': ', '.join(taxes.mapped('name')),
        'tax_amount': total_included - total_excluded,
        'price_with_tax': total_included,
        'tax_details': [
            {
                'name': tax.get('name', ''),
                'amount': tax.get('amount', 0.0),
            }
            for tax in tax_result.get('taxes', [])
        ],
    }


def _wishlist_product_ids(partner):
    if not partner:
        return set()
    items = request.env['lifestyle.wishlist.item'].sudo().search([('partner_id', '=', partner.id)])
    return set(items.mapped('product_tmpl_id').ids)


def _serialize_product(product, wishlist_ids=None):
    tax_info = _product_tax_info(product)
    color_options = [
        value.strip()
        for value in (_store_value(product, 'color_options', '') or '').split(',')
        if value.strip()
    ]
    color_images = {}
    if 'color_image_ids' in product._fields:
        for color_image in product.color_image_ids.filtered(lambda row: row.active and row.image):
            color = (color_image.color_name or '').strip()
            if not color:
                continue
            color_images[color] = _color_row_image_url(color_image.id)
            if color not in color_options:
                color_options.append(color)

    for index in range(1, 5):
        image_field = f'lifestyle_color_image_{index}'
        color_field = f'lifestyle_color_image_{index}_color'
        if image_field not in product._fields or not getattr(product, image_field):
            continue
        selected_color = getattr(product, color_field, False) if color_field in product._fields else False
        fallback_color = color_options[index - 1] if index <= len(color_options) else ''
        color = (selected_color or fallback_color or '').strip()
        if color and color not in color_images:
            color_images[color] = _color_image_url(product.id, index)
    return {
        'id': product.id,
        'name': product.name,
        'description': product.description_sale or '',
        'price': product.list_price,
        'price_with_tax': tax_info['price_with_tax'],
        'tax_amount': tax_info['tax_amount'],
        'tax_label': tax_info['tax_label'],
        'tax_details': tax_info['tax_details'],
        'compare_price': _store_value(product, 'compare_price', 0.0) or 0.0,
        'currency': product.currency_id.symbol or product.currency_id.name,
        'category_id': product.categ_id.id,
        'category_name': product.categ_id.name,
        'has_image': bool(product.image_1920),
        'image_url': _product_image_url(product.id),
        'additional_images': [
            _store_image_url(product.id, image_number)
            for image_number in (2, 3, 4)
            if f'store_image_{image_number}' in product._fields and getattr(product, f'store_image_{image_number}')
        ],
        'store_description': _store_value(product, 'store_description', '') or '',
        'color_options': color_options,
        'color_images': color_images,
        'size_options': [
            value.strip()
            for value in (_store_value(product, 'size_options', '') or '').split(',')
            if value.strip()
        ],
        'store_rating': _store_value(product, 'store_rating', 0.0) or 0.0,
        'store_review_count': _store_value(product, 'store_review_count', 0) or 0,
        'store_sold_count': _store_value(product, 'store_sold_count', 0) or 0,
        'store_sequence': _store_value(product, 'store_sequence', 10) or 10,
        'available_qty': max(0, int(product.qty_available)) if product.type in ('consu', 'product') else 999999,
        'in_stock': product.qty_available > 0 if product.type in ('consu', 'product') else True,
        'in_wishlist': product.id in (wishlist_ids or set()),
    }

class LifestyleAPI(http.Controller):

    # ---------------------------------------------------------------
    # Auth
    # ---------------------------------------------------------------
    @http.route('/lifestyle/api/auth/register', type='json', auth='public', methods=['POST'], csrf=False)
    def register(self, name=None, email=None, password=None, phone=None, **kwargs):
        if not name or not email or not password:
            return {'status': 'error', 'message': 'name, email and password are required.'}
        if len(password) < 6:
            return {'status': 'error', 'message': 'Password must be at least 6 characters.'}

        Users = request.env['res.users'].sudo()
        if Users.search_count([('login', '=', email)]):
            return {'status': 'error', 'message': 'An account with this email already exists.'}

        portal_group = request.env.ref('base.group_portal')
        partner = request.env['res.partner'].sudo().create({
            'name': name,
            'email': email,
            'phone': phone or False,
            'company_type': 'person',
        })
        user = Users.create({
            'name': name,
            'login': email,
            'password': password,
            'partner_id': partner.id,
            'group_ids': [(6, 0, [portal_group.id])],
        })
        return {'status': 'success', 'partner_id': partner.id, 'user_id': user.id}

    # ---------------------------------------------------------------
    # Catalog (public)
    # ---------------------------------------------------------------
    @http.route('/lifestyle/api/banners', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def banners(self, **kwargs):
        banners = request.env['lifestyle.app.banner'].sudo().search([('active', '=', True)], order='sequence, id')
        return {
            'status': 'success',
            'banners': [{
                'id': banner.id,
                'title': banner.title,
                'subtitle': banner.subtitle or '',
                'has_image': bool(banner.image),
                'image_url': _banner_image_url(banner.id) if banner.image else '',
                'background_style': banner.background_style or 'charcoal',
                'background_color': banner.background_color or '',
            } for banner in banners],
        }
    @http.route('/lifestyle/api/categories', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def categories(self, **kwargs):
        roots = [
            request.env.ref('lifestyle_connector.category_fruits_veg').id,
            request.env.ref('lifestyle_connector.category_healthy_pantry').id,
            request.env.ref('lifestyle_connector.category_furniture_home').id,
        ]
        cats = request.env['product.category'].sudo().search([('id', 'child_of', roots)], order='complete_name')
        return {
            'status': 'success',
            'categories': [{'id': c.id, 'name': c.name} for c in cats],
        }

    @http.route('/lifestyle/api/products', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def products(self, category_id=None, search=None, limit=20, offset=0, **kwargs):
        domain = [('sale_ok', '=', True), ('active', '=', True)] + _app_visibility_domain(request.env['product.template'])
        if category_id:
            domain.append(('categ_id', '=', int(category_id)))
        if search:
            domain.append(('name', 'ilike', search))

        Product = request.env['product.template'].sudo()
        limit = min(int(limit or 20), 100)
        offset = int(offset or 0)
        order_by = 'store_sequence, name' if 'store_sequence' in Product._fields else 'name'
        products = Product.search(domain, order=order_by, limit=limit, offset=offset)
        total_count = Product.search_count(domain)
        wishlist_ids = _wishlist_product_ids(_current_partner())

        return {
            'status': 'success',
            'total_count': total_count,
            'count': len(products),
            'offset': offset,
            'products': [_serialize_product(p, wishlist_ids) for p in products],
        }

    @http.route('/lifestyle/api/products/<int:product_id>', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def product_detail(self, product_id, **kwargs):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists() or not product.active or not _is_app_visible(product):
            return {'status': 'error', 'message': 'Product not found'}
        wishlist_ids = _wishlist_product_ids(_current_partner())
        data = _serialize_product(product, wishlist_ids)
        data['description_full'] = product.description or ''
        return {'status': 'success', 'product': data}

    @http.route('/lifestyle/api/wishlist', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def wishlist(self, **kwargs):
        partner = _current_partner()
        if not partner:
            return {'status': 'error', 'message': 'Please log in to continue.'}

        items = request.env['lifestyle.wishlist.item'].sudo().search([('partner_id', '=', partner.id)])
        wishlist_ids = set(items.mapped('product_tmpl_id').ids)
        products = items.mapped('product_tmpl_id').filtered(lambda p: p.active and _is_app_visible(p))
        return {
            'status': 'success',
            'products': [_serialize_product(p, wishlist_ids) for p in products],
        }

    @http.route('/lifestyle/api/wishlist/toggle', type='json', auth='public', methods=['POST'], csrf=False)
    def wishlist_toggle(self, product_id=None, **kwargs):
        partner = _current_partner()
        if not partner:
            return {'status': 'error', 'message': 'Please log in to continue.'}
        if not product_id:
            return {'status': 'error', 'message': 'product_id is required.'}

        product = request.env['product.template'].sudo().browse(int(product_id))
        if not product.exists():
            return {'status': 'error', 'message': 'Product not found'}

        Wishlist = request.env['lifestyle.wishlist.item'].sudo()
        existing = Wishlist.search([
            ('partner_id', '=', partner.id),
            ('product_tmpl_id', '=', product.id),
        ], limit=1)
        if existing:
            existing.unlink()
            return {'status': 'success', 'in_wishlist': False}
        Wishlist.create({'partner_id': partner.id, 'product_tmpl_id': product.id})
        return {'status': 'success', 'in_wishlist': True}

    @http.route('/lifestyle/api/products/<int:product_id>/reviews', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def product_reviews(self, product_id, **kwargs):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists() or not _is_app_visible(product):
            return {'status': 'error', 'message': 'Product not found'}

        partner = _current_partner()
        my_review = None
        if partner:
            mine = product.review_ids.filtered(lambda r: r.partner_id.id == partner.id)
            if mine:
                my_review = {'id': mine.id, 'rating': mine.rating, 'comment': mine.comment or ''}

        return {
            'status': 'success',
            'average_rating': product.store_rating,
            'review_count': product.store_review_count,
            'my_review': my_review,
            'reviews': [{
                'id': review.id,
                'rating': review.rating,
                'comment': review.comment or '',
                'author_name': review.partner_id.name or 'Customer',
                'create_date': str(review.create_date),
            } for review in product.review_ids],
        }

    @http.route('/lifestyle/api/products/<int:product_id>/reviews/submit', type='json', auth='public', methods=['POST'], csrf=False)
    def product_review_submit(self, product_id, rating=None, comment=None, **kwargs):
        partner = _current_partner()
        if not partner:
            return {'status': 'error', 'message': 'Please log in to continue.'}

        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists() or not _is_app_visible(product):
            return {'status': 'error', 'message': 'Product not found'}

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return {'status': 'error', 'message': 'rating must be a number from 1 to 5.'}
        if rating < 1 or rating > 5:
            return {'status': 'error', 'message': 'rating must be between 1 and 5.'}

        Review = request.env['lifestyle.product.review'].sudo()
        existing = Review.search([
            ('product_tmpl_id', '=', product.id),
            ('partner_id', '=', partner.id),
        ], limit=1)
        vals = {'rating': rating, 'comment': (comment or '').strip()}
        if existing:
            existing.write(vals)
        else:
            vals.update({'product_tmpl_id': product.id, 'partner_id': partner.id})
            Review.create(vals)

        product.invalidate_recordset(['store_rating', 'store_review_count'])
        return {
            'status': 'success',
            'average_rating': product.store_rating,
            'review_count': product.store_review_count,
        }

    @http.route('/lifestyle/api/products/<int:product_id>/reviews/delete', type='json', auth='public', methods=['POST'], csrf=False)
    def product_review_delete(self, product_id, **kwargs):
        partner = _current_partner()
        if not partner:
            return {'status': 'error', 'message': 'Please log in to continue.'}

        Review = request.env['lifestyle.product.review'].sudo()
        review = Review.search([
            ('product_tmpl_id', '=', product_id),
            ('partner_id', '=', partner.id),
        ], limit=1)
        if not review:
            return {'status': 'error', 'message': 'You have not reviewed this product.'}

        product = review.product_tmpl_id
        review.unlink()
        product.invalidate_recordset(['store_rating', 'store_review_count'])
        return {
            'status': 'success',
            'average_rating': product.store_rating,
            'review_count': product.store_review_count,
        }

    @http.route('/lifestyle/api/image/banner/<int:banner_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def banner_image(self, banner_id, **kwargs):
        banner = request.env['lifestyle.app.banner'].sudo().browse(banner_id)
        if not banner.exists() or not banner.active or not banner.image:
            return request.not_found()
        return Response(
            base64.b64decode(banner.image),
            content_type='image/png',
            headers={'Cache-Control': 'public, max-age=3600'},
        )
    @http.route('/lifestyle/api/image/product/<int:product_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def product_image(self, product_id, **kwargs):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists() or not _is_app_visible(product) or not product.image_1920:
            return request.not_found()
        return Response(
            base64.b64decode(product.image_1920),
            content_type='image/png',
            headers={'Cache-Control': 'public, max-age=3600'},
        )

    @http.route('/lifestyle/api/image/product/<int:product_id>/store/<int:image_number>', type='http', auth='public', methods=['GET'], csrf=False)
    def product_store_image(self, product_id, image_number, **kwargs):
        if image_number not in (2, 3, 4):
            return request.not_found()
        product = request.env['product.template'].sudo().browse(product_id)
        field_name = f'store_image_{image_number}'
        if not product.exists() or not _is_app_visible(product) or field_name not in product._fields:
            return request.not_found()
        image_data = getattr(product, field_name)
        if not image_data:
            return request.not_found()
        return Response(
            base64.b64decode(image_data),
            content_type='image/png',
            headers={'Cache-Control': 'public, max-age=3600'},
        )

    @http.route('/lifestyle/api/image/product/<int:product_id>/color/<int:image_number>', type='http', auth='public', methods=['GET'], csrf=False)
    def product_color_image(self, product_id, image_number, **kwargs):
        if image_number not in (1, 2, 3, 4):
            return request.not_found()
        product = request.env['product.template'].sudo().browse(product_id)
        field_name = f'lifestyle_color_image_{image_number}'
        if not product.exists() or not _is_app_visible(product) or field_name not in product._fields:
            return request.not_found()
        image_data = getattr(product, field_name)
        if not image_data:
            return request.not_found()
        return Response(
            base64.b64decode(image_data),
            content_type='image/png',
            headers={'Cache-Control': 'public, max-age=3600'},
        )

    @http.route('/lifestyle/api/image/product/color-row/<int:color_image_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def product_color_row_image(self, color_image_id, **kwargs):
        color_image = request.env['lifestyle.product.color.image'].sudo().browse(color_image_id)
        if not color_image.exists() or not color_image.active or not color_image.image:
            return request.not_found()
        product = color_image.product_tmpl_id
        if not product.exists() or not _is_app_visible(product):
            return request.not_found()
        return Response(
            base64.b64decode(color_image.image),
            content_type='image/png',
            headers={'Cache-Control': 'public, max-age=3600'},
        )

    @http.route('/lifestyle/api/image/attachment/<int:attachment_id>/<string:token>', type='http', auth='public', methods=['GET'], csrf=False)
    def attachment_image(self, attachment_id, token, **kwargs):
        grant = request.env['lifestyle.attachment.token'].sudo().search([
            ('attachment_id', '=', attachment_id),
            ('token', '=', token),
        ], limit=1)
        if not grant:
            return request.not_found()
        attachment = grant.attachment_id
        if not attachment.exists() or not attachment.raw:
            return request.not_found()
        return Response(
            attachment.raw,
            content_type=attachment.mimetype or 'image/jpeg',
            headers={'Cache-Control': 'private, max-age=86400'},
        )

    # ---------------------------------------------------------------
    # Device registration (requires login)
    # ---------------------------------------------------------------
    @http.route('/lifestyle/api/device/register', type='json', auth='public', methods=['POST'], csrf=False)
    def register_device(self, token=None, platform='android', **kwargs):
        partner = _current_partner()
        if not partner:
            return {'status': 'error', 'message': 'Please log in to continue.'}
        if not token:
            return {'status': 'error', 'message': 'token is required.'}
        request.env['lifestyle.device.token'].sudo().register(partner, token, platform)
        return {'status': 'success'}

    # ---------------------------------------------------------------
    # Profile (requires login)
    # ---------------------------------------------------------------
    ADDRESS_FIELDS = ('phone', 'street', 'street2', 'city', 'zip')

    def _serialize_profile(self, partner):
        data = {'name': partner.name, 'email': partner.email or ''}
        for field in self.ADDRESS_FIELDS:
            data[field] = getattr(partner, field) or ''
        return data

    @http.route('/lifestyle/api/profile', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def profile(self, **kwargs):
        partner = _current_partner()
        if not partner:
            return {'status': 'error', 'message': 'Please log in to continue.'}
        return {'status': 'success', 'profile': self._serialize_profile(partner)}

    @http.route('/lifestyle/api/profile/update', type='json', auth='public', methods=['POST'], csrf=False)
    def update_profile(self, name=None, phone=None, street=None, street2=None, city=None, zip=None, **kwargs):
        partner = _current_partner()
        if not partner:
            return {'status': 'error', 'message': 'Please log in to continue.'}

        vals = {}
        if name is not None:
            vals['name'] = name
        for field, value in (('phone', phone), ('street', street), ('street2', street2), ('city', city), ('zip', zip)):
            if value is not None:
                vals[field] = value
        if vals:
            partner.sudo().write(vals)
        return {'status': 'success', 'profile': self._serialize_profile(partner)}

    # ---------------------------------------------------------------
    # Checkout & Orders (require login)
    # ---------------------------------------------------------------
    @http.route('/lifestyle/api/checkout', type='json', auth='public', methods=['POST'], csrf=False)
    def checkout(self, fulfillment_type='delivery', lines=None, note=None,
                 phone=None, street=None, street2=None, city=None, zip=None, **kwargs):
        partner = _current_partner()
        if not partner:
            return {'status': 'error', 'message': 'Please log in to continue.'}
        if fulfillment_type not in ('delivery', 'pickup'):
            return {'status': 'error', 'message': 'fulfillment_type must be delivery or pickup.'}
        if not lines:
            return {'status': 'error', 'message': 'At least one order line is required.'}

        if fulfillment_type == 'delivery':
            address_vals = {}
            for field, value in (('phone', phone), ('street', street), ('street2', street2), ('city', city), ('zip', zip)):
                if value is not None:
                    address_vals[field] = value
            if address_vals:
                partner.sudo().write(address_vals)

        ProductTemplate = request.env['product.template'].sudo()
        order_lines = []
        for line in lines:
            template = ProductTemplate.browse(int(line.get('product_id', 0)))
            qty = float(line.get('qty', 1))
            if (
                not template.exists()
                or not template.active
                or not template.sale_ok
                or not _is_app_visible(template)
                or qty <= 0
            ):
                return {'status': 'error', 'message': f'Invalid product or quantity: {line}'}
            product = template.product_variant_id
            if not product:
                return {'status': 'error', 'message': f'No sellable variant found for: {template.name}'}
            if template.type in ('consu', 'product'):
                requested_qty = sum(
                    float(existing.get('qty', 1))
                    for existing in lines
                    if int(existing.get('product_id', 0)) == template.id
                )
                if requested_qty > template.qty_available:
                    available = max(0, int(template.qty_available))
                    return {
                        'status': 'error',
                        'message': f'Only {available} available for: {template.name}',
                    }
            selected_color = (line.get('color') or '').strip()
            color_options = []
            if 'color_options' in template._fields and template.color_options:
                color_options = [value.strip() for value in template.color_options.split(',') if value.strip()]
            if color_options and selected_color not in color_options:
                return {'status': 'error', 'message': f'Select a valid color for: {template.name}'}
            line_vals = {'product_id': product.id, 'product_uom_qty': qty}
            if selected_color:
                line_vals['lifestyle_color'] = selected_color
                line_vals['name'] = f'{product.display_name}\nColor: {selected_color}'
            order_lines.append((0, 0, line_vals))

        order = request.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'fulfillment_type': fulfillment_type,
            'note': note or False,
            'order_line': order_lines,
        })
        order.action_confirm()
        return {'status': 'success', 'order_id': order.id, 'order_name': order.name}

    @http.route('/lifestyle/api/orders', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def orders(self, limit=20, offset=0, **kwargs):
        partner = _current_partner()
        if not partner:
            return {'status': 'error', 'message': 'Please log in to continue.'}

        Order = request.env['sale.order'].sudo()
        domain = [('partner_id', '=', partner.id)]
        orders = Order.search(domain, order='date_order desc', limit=min(int(limit or 20), 100), offset=int(offset or 0))
        return {
            'status': 'success',
            'orders': [{
                'id': o.id,
                'name': o.name,
                'date_order': str(o.date_order),
                'state': o.state,
                'fulfillment_type': o.fulfillment_type,
                'delivery_stage': o.delivery_stage,
                'stage_label': STAGE_LABELS.get(o.delivery_stage, o.delivery_stage),
                'progress_percent': o.lifestyle_progress_percent or 0,
                'amount_total': o.amount_total,
                'currency': o.currency_id.symbol or o.currency_id.name,
            } for o in orders],
        }

    @http.route('/lifestyle/api/orders/<int:order_id>', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def order_detail(self, order_id, **kwargs):
        partner = _current_partner()
        if not partner:
            return {'status': 'error', 'message': 'Please log in to continue.'}

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.partner_id.id != partner.id:
            return {'status': 'error', 'message': 'Order not found'}

        return {
            'status': 'success',
            'order': {
                'id': order.id,
                'name': order.name,
                'date_order': str(order.date_order),
                'state': order.state,
                'fulfillment_type': order.fulfillment_type,
                'delivery_stage': order.delivery_stage,
                'progress_percent': order.lifestyle_progress_percent or 0,
                'amount_total': order.amount_total,
                'currency': order.currency_id.symbol or order.currency_id.name,
                'timeline': _timeline_for(order),
                'photo_url': order._lifestyle_photo_url(),
                'media_url': order._lifestyle_media_url(),
                'media_mimetype': order._lifestyle_media_mimetype(),
                'media_list': order._lifestyle_media_list(),
                'lines': [{
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                    'color': line.lifestyle_color or '',
                } for line in order.order_line],
            },
        }

    # ---------------------------------------------------------------
    # Vendor tools (internal staff only - surfaced in the app's Profile
    # page when the logged-in account is Odoo staff, not a portal customer)
    # ---------------------------------------------------------------
    @http.route('/lifestyle/api/whoami', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def whoami(self, **kwargs):
        user = request.env.user
        if not user or user._is_public():
            return {'status': 'error', 'message': 'Please log in to continue.'}
        return {
            'status': 'success',
            'is_staff': _is_staff(),
            'name': user.name,
            'email': user.login,
        }

    @http.route('/lifestyle/api/vendor/login', type='json', auth='public', methods=['POST'], csrf=False)
    def vendor_login(self, email=None, pin=None, **kwargs):
        if not email or not pin:
            return {'status': 'error', 'message': 'email and pin are required.'}

        employee = request.env['hr.employee'].sudo().search([('app_email', '=', email)], limit=1)
        if not employee:
            # No such login email — nothing to rate-limit, just say invalid.
            return {'status': 'error', 'message': 'Invalid email or PIN.'}

        if employee.app_pin_locked_until and employee.app_pin_locked_until > fields.Datetime.now():
            return {'status': 'error', 'message': 'Too many failed attempts. Try again in a few minutes.'}

        if not employee.is_app_active or employee.app_pin != pin:
            employee.app_pin_failed_attempts += 1
            if employee.app_pin_failed_attempts >= 5:
                employee.app_pin_locked_until = fields.Datetime.now() + timedelta(minutes=15)
                employee.app_pin_failed_attempts = 0
            return {'status': 'error', 'message': 'Invalid email or PIN.'}

        employee.app_pin_failed_attempts = 0
        employee.app_pin_locked_until = False

        if employee.staff_role != 'carpenter':
            return {'status': 'error', 'message': 'This account does not have vendor access.'}
        vendor_session = request.env['lifestyle.vendor.session'].sudo().issue_for(employee)
        return {'status': 'success', 'token': vendor_session.token, 'name': employee.name}

    @http.route('/lifestyle/api/vendor/orders', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def vendor_orders(self, limit=20, offset=0, **kwargs):
        if not _vendor_access():
            return {'status': 'error', 'message': 'Vendor access required.'}

        Order = request.env['sale.order'].sudo()
        orders = Order.search([], order='date_order desc', limit=min(int(limit or 20), 100), offset=int(offset or 0))
        return {
            'status': 'success',
            'orders': [{
                'id': o.id,
                'name': o.name,
                'partner_name': o.partner_id.name,
                'date_order': str(o.date_order),
                'state': o.state,
                'fulfillment_type': o.fulfillment_type,
                'delivery_stage': o.delivery_stage,
                'stage_label': STAGE_LABELS.get(o.delivery_stage, o.delivery_stage),
                'progress_percent': o.lifestyle_progress_percent or 0,
                'amount_total': o.amount_total,
                'currency': o.currency_id.symbol or o.currency_id.name,
                'can_send_media': o._lifestyle_can_send_media(),
                'skip_processing': o._lifestyle_skip_processing(),
                'stage_unlocked': o.lifestyle_stage_unlocked,
            } for o in orders],
        }

    @http.route('/lifestyle/api/vendor/orders/<int:order_id>/progress', type='json', auth='public', methods=['POST'], csrf=False)
    def vendor_update_progress(self, order_id, progress_percent=None, **kwargs):
        if not _vendor_access():
            return {'status': 'error', 'message': 'Vendor access required.'}

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'status': 'error', 'message': 'Order not found'}

        try:
            progress = int(progress_percent)
        except Exception:
            return {'status': 'error', 'message': 'progress_percent must be a number.'}
        progress = max(0, min(100, progress))
        order.lifestyle_progress_percent = progress
        order.message_post(body=f'Furniture progress updated: <b>{progress}%</b>')
        if order.partner_id:
            order._lifestyle_send_push_to_partner(
                order.partner_id,
                title=f'Order {order.name}',
                body=f'Your furniture is {progress}% complete.',
                data={'type': 'order_progress', 'order_id': order.id, 'progress_percent': progress},
            )
        return {'status': 'success', 'progress_percent': progress}

    @http.route('/lifestyle/api/vendor/orders/<int:order_id>/stage', type='json', auth='public', methods=['POST'], csrf=False)
    def vendor_update_stage(self, order_id, stage=None, **kwargs):
        if not _vendor_access():
            return {'status': 'error', 'message': 'Vendor access required.'}
        if not stage:
            return {'status': 'error', 'message': 'stage is required.'}

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'status': 'error', 'message': 'Order not found'}

        allowed_stages = PICKUP_STAGE_SEQUENCE if order.fulfillment_type == 'pickup' else DELIVERY_STAGE_SEQUENCE
        if order._lifestyle_skip_processing():
            allowed_stages = [s for s in allowed_stages if s != 'processing']
        if stage not in allowed_stages:
            return {'status': 'error', 'message': 'This stage is not valid for this order.'}
        if stage == 'order_placed':
            return {'status': 'error', 'message': 'Order Placed is set automatically when the order is created.'}

        try:
            order._lifestyle_advance_stage(stage, push=False)
        except Exception as exc:
            return {'status': 'error', 'message': _safe_error_message(exc)}
        return {
            'status': 'success',
            'order': {
                'id': order.id,
                'delivery_stage': order.delivery_stage,
                'stage_label': STAGE_LABELS.get(order.delivery_stage, order.delivery_stage),
                'stage_unlocked': order.lifestyle_stage_unlocked,
            },
        }

    @http.route('/lifestyle/api/vendor/orders/<int:order_id>/stage/notify', type='json', auth='public', methods=['POST'], csrf=False)
    def vendor_notify_stage(self, order_id, **kwargs):
        if not _vendor_access():
            return {'status': 'error', 'message': 'Vendor access required.'}

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'status': 'error', 'message': 'Order not found'}
        try:
            order._lifestyle_send_stage_notification()
        except Exception as exc:
            return {'status': 'error', 'message': _safe_error_message(exc)}
        return {'status': 'success'}

    @http.route('/lifestyle/api/vendor/orders/<int:order_id>/media/list', type='json', auth='public', methods=['GET', 'POST'], csrf=False)
    def vendor_order_media(self, order_id, **kwargs):
        if not _vendor_access():
            return {'status': 'error', 'message': 'Vendor access required.'}
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'status': 'error', 'message': 'Order not found'}
        return {'status': 'success', 'media_list': order._lifestyle_media_list()}

    @http.route('/lifestyle/api/vendor/orders/<int:order_id>/media', type='json', auth='public', methods=['POST'], csrf=False)
    def vendor_send_media(self, order_id, media_base64=None, mimetype='image/jpeg', comment=None, **kwargs):
        if not _vendor_access():
            return {'status': 'error', 'message': 'Vendor access required.'}
        if not media_base64:
            return {'status': 'error', 'message': 'media_base64 is required.'}
        if not (mimetype or '').startswith(('image/', 'video/')):
            return {'status': 'error', 'message': 'Only image and video updates are supported.'}

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'status': 'error', 'message': 'Order not found'}
        if not order.partner_id:
            return {'status': 'error', 'message': 'This order has no customer to notify.'}
        if not order._lifestyle_can_send_media():
            return {'status': 'error', 'message': 'This order has already been completed - no further updates can be sent.'}

        extension = 'mp4' if (mimetype or '').startswith('video/') else 'jpg'
        request.env['ir.attachment'].sudo().create({
            'name': f'{order.name}-furniture-update.{extension}',
            'res_model': 'sale.order',
            'res_id': order.id,
            'mimetype': mimetype,
            'datas': media_base64,
            'description': (comment or '').strip() or False,
        })
        try:
            order.action_send_media_update(new_count=1, comment=(comment or '').strip() or None)
        except Exception as exc:
            return {'status': 'error', 'message': _safe_error_message(exc)}
        return {'status': 'success'}

    @http.route('/lifestyle/api/vendor/orders/<int:order_id>/media/batch', type='json', auth='public', methods=['POST'], csrf=False)
    def vendor_send_media_batch(self, order_id, items=None, comment=None, **kwargs):
        if not _vendor_access():
            return {'status': 'error', 'message': 'Vendor access required.'}
        comment = (comment or '').strip()
        if not items and not comment:
            return {'status': 'error', 'message': 'Add a photo, video, or comment before sending.'}
        items = items or []

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'status': 'error', 'message': 'Order not found'}
        if not order.partner_id:
            return {'status': 'error', 'message': 'This order has no customer to notify.'}
        if not order._lifestyle_can_send_media():
            return {'status': 'error', 'message': 'This order has already been completed - no further updates can be sent.'}

        Attachment = request.env['ir.attachment'].sudo()
        created = 0
        for item in items:
            media_base64 = item.get('media_base64')
            mimetype = item.get('mimetype') or 'image/jpeg'
            if not media_base64 or not mimetype.startswith(('image/', 'video/')):
                continue
            extension = 'mp4' if mimetype.startswith('video/') else 'jpg'
            created += 1
            Attachment.create({
                'name': f'{order.name}-furniture-update-{created}.{extension}',
                'res_model': 'sale.order',
                'res_id': order.id,
                'mimetype': mimetype,
                'datas': media_base64,
                'description': comment or False,
            })

        if not created and comment:
            Attachment.create({
                'name': f'{order.name}-furniture-comment.txt',
                'res_model': 'sale.order',
                'res_id': order.id,
                'mimetype': 'text/plain',
                'datas': base64.b64encode(comment.encode('utf-8')).decode('ascii'),
                'description': comment,
            })
        elif not created:
            return {'status': 'error', 'message': 'No valid photos or videos were provided.'}

        try:
            order.action_send_media_update(new_count=created, comment=comment or None)
        except Exception as exc:
            return {'status': 'error', 'message': _safe_error_message(exc)}
        return {'status': 'success', 'count': created}

    @http.route('/lifestyle/api/vendor/orders/<int:order_id>/photo', type='json', auth='public', methods=['POST'], csrf=False)
    def vendor_send_photo(self, order_id, image_base64=None, mimetype='image/jpeg', **kwargs):
        if not _vendor_access():
            return {'status': 'error', 'message': 'Vendor access required.'}
        if not image_base64:
            return {'status': 'error', 'message': 'image_base64 is required.'}

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'status': 'error', 'message': 'Order not found'}
        if not order.partner_id:
            return {'status': 'error', 'message': 'This order has no customer to notify.'}
        if not order._lifestyle_can_send_media():
            return {'status': 'error', 'message': 'This order has already been completed - no further updates can be sent.'}

        request.env['ir.attachment'].sudo().create({
            'name': f'{order.name}-photo.jpg',
            'res_model': 'sale.order',
            'res_id': order.id,
            'mimetype': mimetype,
            'datas': image_base64,
        })
        try:
            order.action_send_photo_to_customer()
        except Exception as exc:
            return {'status': 'error', 'message': _safe_error_message(exc)}
        return {'status': 'success'}

















