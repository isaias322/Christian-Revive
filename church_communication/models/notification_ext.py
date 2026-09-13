from odoo import models, fields


class ReviveNotificationTargeting(models.Model):
    _inherit = 'revive.notification'

    # revive.notification is what the app's Notifications page actually
    # renders (see OdooService.fetchReviveNotifications / notifications_page
    # .dart) — app.notification is a separate, currently-unused-by-the-app
    # legacy model, so targeting belongs here, not there.
    target_member_ids = fields.Many2many(
        'res.partner', string='Target Members',
        help='Leave empty to show this notification to everyone, as before. '
             'Set specific members to scope it to a segment (see Bulk Messages).',
    )
