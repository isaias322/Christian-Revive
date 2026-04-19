from odoo import fields, models, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import pytz


class LiveStream(models.Model):
    _name = 'crtv.live.stream'
    _description = 'CRTV Live Stream'
    _order = 'air_date asc, air_time asc'
    _rec_name = 'name'

    # ── Basic Info ────────────────────────────────────────────
    name        = fields.Char(string='Program Title', required=True)
    subtitle    = fields.Char(string='Episode / Subtitle')
    description = fields.Text(string='Description')
    thumbnail   = fields.Binary(string='Thumbnail Image')

    # ── Scheduling ────────────────────────────────────────────
    air_date = fields.Date(
        string='Air Date',
        required=True,
        default=fields.Date.today,
    )
    air_time = fields.Char(
        string='Air Time (HH:MM)',
        default='09:00',
        help='24-hour LOCAL time — e.g. 09:00, 14:30, 20:00. '
             'The system will convert to UTC automatically.',
    )
    duration = fields.Integer(
        string='Duration (minutes)',
        default=60,
    )

    # Stored UTC datetimes for efficient querying
    air_datetime_start = fields.Datetime(
        string='Start (UTC)',
        compute='_compute_air_datetimes',
        store=True,
    )
    air_datetime_end = fields.Datetime(
        string='End (UTC)',
        compute='_compute_air_datetimes',
        store=True,
    )

    # Human-readable local time display
    air_datetime_local = fields.Char(
        string='Local Start Time',
        compute='_compute_local_display',
        store=False,
    )

    is_live_now = fields.Boolean(
        string='Live Now',
        compute='_compute_status_auto',
        store=False,
    )

    # ── Stream Source ─────────────────────────────────────────
    stream_type = fields.Selection([
        ('youtube',     'YouTube'),
        ('onedrive',    'OneDrive'),
        ('googledrive', 'Google Drive'),
        ('direct_url',  'Direct URL'),
        ('uploaded',    'Uploaded Video'),
    ], string='Stream Type', default='youtube', required=True)

    stream_url = fields.Char(string='Stream URL')
    video_file = fields.Binary(string='Video File')

    # ── Category & Flags ─────────────────────────────────────
    category = fields.Selection([
        ('live',    'Live Stream'),
        ('program', 'Program'),
        ('sermon',  'Sermon'),
        ('special', 'Special Event'),
        ('sabbath', 'Sabbath School'),
        ('worship', 'Worship Service'),
        ('prayer',  'Prayer Meeting'),
    ], string='Category', default='program', required=True)

    # Auto-computed — no manual editing needed
    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('live',      'On Air'),
        ('ended',     'Ended'),
    ], string='Status', compute='_compute_status_auto', store=True)

    is_published = fields.Boolean(string='Published', default=True)
    is_featured  = fields.Boolean(string='Featured (Main Player)')

    send_notification = fields.Boolean(string='Send Push Notification', default=False)

    # ── Language Selection ─────────────────────
    language = fields.Selection([
        ('english', 'English'),
        ('urdu', 'Urdu'),
    ], string='Language', default='english', required=True)

    # ── Get server/user timezone ──────────────────────────────
    def _get_tz(self):
        """Return the active timezone — user tz > system tz > Asia/Karachi."""
        tz_name = (
            self.env.user.tz
            or self.env['ir.config_parameter'].sudo().get_param(
                'system.timezone', 'Asia/Karachi')
        )
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.timezone('Asia/Karachi')


    # ── Convert local air_date + air_time → UTC Datetime ─────
    @api.depends('air_date', 'air_time', 'duration')
    def _compute_air_datetimes(self):
        for rec in self:
            try:
                h, m = map(int, (rec.air_time or '00:00').split(':'))
                tz = rec._get_tz()

                # Build naive local datetime
                local_naive = datetime(
                    rec.air_date.year,
                    rec.air_date.month,
                    rec.air_date.day,
                    h, m, 0,
                )

                # Localise → convert to UTC → strip tzinfo for Odoo storage
                local_aware = tz.localize(local_naive, is_dst=None)
                utc_start   = local_aware.astimezone(pytz.UTC).replace(tzinfo=None)
                utc_end     = utc_start + timedelta(minutes=rec.duration or 60)

                rec.air_datetime_start = utc_start
                rec.air_datetime_end   = utc_end

            except Exception:
                rec.air_datetime_start = False
                rec.air_datetime_end   = False

    # ── Human-readable local time display ─────────────────────
    def _compute_local_display(self):
        for rec in self:
            try:
                if not rec.air_datetime_start:
                    rec.air_datetime_local = ''
                    continue
                tz = rec._get_tz()
                local_dt = pytz.UTC.localize(
                    rec.air_datetime_start).astimezone(tz)
                rec.air_datetime_local = local_dt.strftime('%Y-%m-%d %H:%M (%Z)')
            except Exception:
                rec.air_datetime_local = ''

    # ── Auto status from current UTC time ─────────────────────
    @api.depends('air_datetime_start', 'air_datetime_end')
    def _compute_status_auto(self):
        now_utc = datetime.utcnow()
        for rec in self:
            try:
                start = rec.air_datetime_start
                end   = rec.air_datetime_end
                if not start or not end:
                    rec.status      = 'scheduled'
                    rec.is_live_now = False
                elif now_utc < start:
                    rec.status      = 'scheduled'
                    rec.is_live_now = False
                elif start <= now_utc <= end:
                    rec.status      = 'live'
                    rec.is_live_now = True
                else:
                    rec.status      = 'ended'
                    rec.is_live_now = False
            except Exception:
                rec.status      = 'scheduled'
                rec.is_live_now = False

    # ── Cron: refresh all statuses every minute ───────────────
    def action_refresh_all_statuses(self):
        """Called by the scheduler every minute."""
        records = self.search([('is_published', '=', True)])
        now_utc = datetime.utcnow()
        for rec in records:
            start = rec.air_datetime_start
            end   = rec.air_datetime_end
            if not start or not end:
                new_status = 'scheduled'
            elif now_utc < start:
                new_status = 'scheduled'
            elif start <= now_utc <= end:
                new_status = 'live'
            else:
                new_status = 'ended'
            if rec.status != new_status:
                rec.write({'status': new_status})


    # ── Constraint: validate HH:MM format ────────────────────
    @api.constrains('air_time')
    def _check_air_time(self):
        import re
        for rec in self:
            if rec.air_time and not re.match(r'^\d{2}:\d{2}$', rec.air_time):
                raise ValidationError(   # ✅ from odoo.exceptions
                    'Air Time must be HH:MM format — e.g. 09:00 or 14:30'
                )