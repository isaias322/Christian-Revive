# -*- coding: utf-8 -*-
from odoo import models, fields


class AppNotificationOv27(models.Model):
    _inherit = 'app.notification'

    notification_type = fields.Selection(
        selection_add=[('onevoice', 'OneVoice27')],
        ondelete={'onevoice': 'set default'},
    )
