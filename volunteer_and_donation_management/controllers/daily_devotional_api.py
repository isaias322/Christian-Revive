import json
import base64
from odoo import http
from odoo.http import request, Response


class DailyDevotionalAPI(http.Controller):

    @http.route('/api/devotionals', type='http', auth='public', methods=['GET'], csrf=False)
    def get_devotionals(self, **kwargs):
        limit = int(kwargs.get('limit', 20))
        offset = int(kwargs.get('offset', 0))

        devotionals = request.env['daily.devotional'].sudo().search(
            [('is_published', '=', True)],
            order='date desc',
            limit=limit,
            offset=offset,
        )

        total_count = request.env['daily.devotional'].sudo().search_count(
            [('is_published', '=', True)]
        )

        result = []
        for dev in devotionals:
            result.append({
                'id': dev.id,
                'title': dev.name,
                'date': dev.date.strftime('%b %d, %Y') if dev.date else '',
                'date_raw': str(dev.date) if dev.date else '',
                'summary': dev.summary or '',
                'scripture_reference': dev.scripture_reference or '',
                'author': dev.author or '',
                'category': dev.category or '',
                'has_image': bool(dev.image),
            })

        data = {
            'status': 'success',
            'total_count': total_count,
            'count': len(result),
            'offset': offset,
            'devotionals': result,
        }

        return request.make_json_response(data)

    @http.route('/api/devotionals/<int:devotional_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def get_devotional_detail(self, devotional_id, **kwargs):
        devotional = request.env['daily.devotional'].sudo().browse(devotional_id)

        if not devotional.exists() or not devotional.is_published:
            return request.make_json_response(
                {'status': 'error', 'message': 'Devotional not found'},
                status=404,
            )

        image_url = ''
        if devotional.image:
            image_url = '/api/devotionals/%d/image' % devotional.id

        data = {
            'status': 'success',
            'devotional': {
                'id': devotional.id,
                'title': devotional.name,
                'date': devotional.date.strftime('%b %d, %Y') if devotional.date else '',
                'date_raw': str(devotional.date) if devotional.date else '',
                'content': devotional.content or '',
                'summary': devotional.summary or '',
                'scripture_reference': devotional.scripture_reference or '',
                'author': devotional.author or '',
                'category': devotional.category or '',
                'image_url': image_url,
            },
        }

        return request.make_json_response(data)

    @http.route('/api/devotionals/<int:devotional_id>/image', type='http', auth='public', methods=['GET'], csrf=False)
    def get_devotional_image(self, devotional_id, **kwargs):
        devotional = request.env['daily.devotional'].sudo().browse(devotional_id)

        if not devotional.exists() or not devotional.image:
            return request.not_found()

        image_data = base64.b64decode(devotional.image)
        return Response(
            image_data,
            content_type='image/png',
            headers={'Cache-Control': 'public, max-age=86400'},
        )