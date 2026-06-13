from odoo import models, fields

class MusicTrack(models.Model):
    _name = 'music.track'
    _description = 'Music Track'
    _order = 'sequence asc, create_date desc'

    name = fields.Char(string='Song Title', required=True)
    artist = fields.Char(string='Artist', default='Titus Major')
    album = fields.Char(string='Album')
    # ── Source ──────────────────────────────────
    source_type = fields.Selection([
        ('youtube', 'YouTube'),
        ('onedrive', 'OneDrive'),
        ('upload', 'Upload MP3'),
    ], string='Source', default='youtube', required=True)
    youtube_url = fields.Char(string='YouTube URL')
    onedrive_url = fields.Char(string='OneDrive Video Link')
    audio_file = fields.Binary(string='MP3 File', attachment=True)
    audio_filename = fields.Char(string='MP3 Filename')
    duration = fields.Char(string='Duration', help='e.g. 4:32')
    genre = fields.Char(string='Genre', default='Gospel')
    # ── Language Selection ─────────────────────
    language = fields.Selection([
        ('english', 'English'),
        ('urdu', 'Urdu'),
    ], string='Language', default='english', required=True)
    sequence = fields.Integer(default=10)
    is_published = fields.Boolean(default=True)
    is_featured = fields.Boolean(string='Featured')
    description = fields.Text()
    lyrics = fields.Text()
    image = fields.Binary(string='Cover Art')

    @property
    def youtube_id(self):
        url = self.youtube_url or ''
        if 'v=' in url:
            return url.split('v=')[-1].split('&')[0]
        if 'youtu.be/' in url:
            return url.split('youtu.be/')[-1].split('?')[0]
        return url