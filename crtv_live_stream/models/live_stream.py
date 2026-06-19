import logging

from odoo import fields, models, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import pytz

_logger = logging.getLogger(__name__)


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
        default=lambda self: self._default_air_date_and_time()[0],
        index=True,
    )
    air_time = fields.Char(
        string='Air Time (HH:MM)',
        default=lambda self: self._default_air_date_and_time()[1],
        help='24-hour LOCAL time — e.g. 09:00, 14:30, 20:00. '
             'The system will convert to UTC automatically. '
             'Defaults to right after the most recently scheduled program ends.',
    )
    duration = fields.Integer(
        string='Duration (minutes)',
        default=60,
    )

    # Stored UTC datetimes for efficient querying — indexed for cron + status filters
    air_datetime_start = fields.Datetime(
        string='Start (UTC)',
        compute='_compute_air_datetimes',
        store=True,
        index=True,
    )
    air_datetime_end = fields.Datetime(
        string='End (UTC)',
        compute='_compute_air_datetimes',
        store=True,
        index=True,
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

    # ── Default a new record to start right after the previous one ends ──
    def _default_air_date_and_time(self):
        last = self.search([], order='air_date desc, air_time desc', limit=1)
        if not last or not last.air_time:
            return fields.Date.today(), '09:00'
        try:
            h, m = map(int, last.air_time.split(':'))
        except Exception:
            return fields.Date.today(), '09:00'
        total_minutes = h * 60 + m + (last.duration or 60)
        days_forward, minutes_of_day = divmod(total_minutes, 24 * 60)
        new_date = last.air_date + timedelta(days=days_forward)
        new_time = '%02d:%02d' % (minutes_of_day // 60, minutes_of_day % 60)
        return new_date, new_time

    # ── Auto-detect video duration ────────────────────────────
    def _fetch_youtube_duration_minutes(self, url):
        """Look up a YouTube video's duration via yt-dlp (no API key needed).
        Returns whole minutes (rounded up), or False if it can't be determined."""
        if not url:
            return False
        try:
            import yt_dlp
        except ImportError:
            _logger.warning('yt-dlp is not installed — cannot auto-detect duration for %s', url)
            return False
        try:
            opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            seconds = info.get('duration') if info else None
            if not seconds:
                _logger.warning('yt-dlp returned no duration for %s (info=%s)', url, info)
                return False
            return max(1, -(-int(seconds) // 60))
        except Exception:
            _logger.exception('yt-dlp failed to fetch duration for %s', url)
            return False

    def _fetch_file_duration_minutes(self, video_binary):
        """Inspect an uploaded video file's duration via ffprobe.
        Returns whole minutes (rounded up), or False if it can't be determined."""
        if not video_binary:
            return False
        import base64, subprocess, tempfile, os, json
        try:
            raw = base64.b64decode(video_binary)
        except Exception:
            return False
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'json', tmp_path],
                capture_output=True, text=True, timeout=30,
            )
            data = json.loads(result.stdout or '{}')
            seconds = float(data.get('format', {}).get('duration') or 0)
            if not seconds:
                _logger.warning('ffprobe returned no duration (stderr=%s)', result.stderr)
                return False
            return max(1, -(-int(seconds) // 60))
        except Exception:
            _logger.exception('ffprobe failed to read uploaded video duration')
            return False
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

    @api.onchange('stream_type', 'stream_url')
    def _onchange_stream_url_duration(self):
        if self.stream_type == 'youtube' and self.stream_url:
            minutes = self._fetch_youtube_duration_minutes(self.stream_url)
            if minutes:
                self.duration = minutes

    @api.onchange('stream_type', 'video_file')
    def _onchange_video_file_duration(self):
        if self.stream_type == 'uploaded' and self.video_file:
            minutes = self._fetch_file_duration_minutes(self.video_file)
            if minutes:
                self.duration = minutes

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('duration'):
                continue
            minutes = False
            if vals.get('stream_type') == 'youtube' and vals.get('stream_url'):
                minutes = self._fetch_youtube_duration_minutes(vals['stream_url'])
            elif vals.get('stream_type') == 'uploaded' and vals.get('video_file'):
                minutes = self._fetch_file_duration_minutes(vals['video_file'])
            if minutes:
                vals['duration'] = minutes
        return super().create(vals_list)

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