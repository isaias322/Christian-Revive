from odoo import models, fields, api


class HymnCollection(models.Model):
    _name = 'hymn.collection'
    _description = 'Hymn Collection / Song Book'
    _order = 'sequence, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Collection Name', required=True, tracking=True,
                       help='e.g. "Hymns Book", "گیت و زبور"')
    code = fields.Char(string='Code', required=True,
                       help='Internal code used by the app, e.g. "hymns", "geet_zaboor"')
    description = fields.Text(string='Description')
    language = fields.Selection([
        ('english', 'English'),
        ('urdu', 'اردو (Urdu)'),
        ('punjabi', 'پنجابی (Punjabi)'),
        ('hindi', 'हिन्दी (Hindi)'),
        ('arabic', 'العربية (Arabic)'),
        ('roman_urdu', 'Roman Urdu'),
        ('multi', 'Multi-Language'),
    ], string='Primary Language', default='english', required=True, tracking=True)
    image = fields.Binary(string='Cover Image', attachment=True)
    is_published = fields.Boolean(string='Published', default=True, tracking=True)
    sequence = fields.Integer(string='Display Order', default=10)
    color = fields.Char(string='Theme Color (Hex)', default='#4A3728',
                        help='Hex color code for the app UI, e.g. #4A3728')

    # ── Computed ──
    song_count = fields.Integer(string='Songs', compute='_compute_song_count')
    category_summary = fields.Char(string='Categories', compute='_compute_category_summary')

    # ── Relationships ──
    song_ids = fields.One2many('hymn.song', 'collection_id', string='Songs')

    @api.depends('song_ids')
    def _compute_song_count(self):
        for rec in self:
            rec.song_count = len(rec.song_ids)

    @api.depends('song_ids.category_id')
    def _compute_category_summary(self):
        for rec in self:
            cats = rec.song_ids.mapped('category_id.name')
            rec.category_summary = ', '.join(set(cats)) if cats else ''

    def action_view_songs(self):
        """Open songs filtered by this collection."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Songs - {self.name}',
            'res_model': 'hymn.song',
            'view_mode': 'tree,form',
            'domain': [('collection_id', '=', self.id)],
            'context': {'default_collection_id': self.id},
        }

    # ── API for Flutter ──
    @api.model
    def app_fetch_collections(self, *args, **kwargs):
        """Return published collections for the mobile app."""
        collections = self.search([('is_published', '=', True)], order='sequence, id')
        return [{
            'id': c.id,
            'name': c.name,
            'code': c.code,
            'description': c.description or '',
            'language': c.language,
            'color': c.color or '#4A3728',
            'song_count': c.song_count,
            'has_image': bool(c.image),
        } for c in collections]