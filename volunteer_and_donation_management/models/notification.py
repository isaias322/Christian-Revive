from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AppNotification(models.Model):
    _name = 'app.notification'
    _description = 'App Notification'
    _order = 'create_date desc'

    name = fields.Char(string='Title', required=True)
    message = fields.Text(string='Message')
    image = fields.Binary(string='Image')
    notification_type = fields.Selection([
        ('info', 'Info'),
        ('alert', 'Alert'),
        ('event', 'Event'),
        ('sermon', 'Sermon'),
    ], default='info')
    is_published = fields.Boolean(default=True)
    target_url = fields.Char(string='Link URL')
    create_date = fields.Datetime(readonly=True)

    # ── Scheduling ──────────────────────────────────────
    is_scheduled = fields.Boolean(
        string='Schedule This Notification',
        default=False,
        help='If enabled, notification only shows between publish and expiry dates'
    )
    scheduled_publish = fields.Datetime(
        string='Publish At',
        help='Notification becomes visible from this date/time'
    )
    scheduled_expiry = fields.Datetime(
        string='Expire At',
        help='Notification stops showing after this date/time'
    )

    # ── Computed: is it currently active? ───────────────
    is_active_now = fields.Boolean(
        string='Active Now',
        compute='_compute_is_active_now',
        store=False,
    )

    @api.depends('is_published', 'is_scheduled', 'scheduled_publish', 'scheduled_expiry')
    def _compute_is_active_now(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.is_published:
                rec.is_active_now = False
                continue
            if not rec.is_scheduled:
                rec.is_active_now = True
                continue
            # Scheduled: check window
            after_publish = (rec.scheduled_publish is False or now >= rec.scheduled_publish)
            before_expiry = (rec.scheduled_expiry is False or now <= rec.scheduled_expiry)
            rec.is_active_now = after_publish and before_expiry

    @api.constrains('scheduled_publish', 'scheduled_expiry')
    def _check_dates(self):
        for rec in self:
            if rec.scheduled_publish and rec.scheduled_expiry:
                if rec.scheduled_publish >= rec.scheduled_expiry:
                    raise ValidationError('Expire At must be after Publish At.')