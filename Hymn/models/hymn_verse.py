from odoo import models, fields


class HymnVerse(models.Model):
    _name = 'hymn.verse'
    _description = 'Hymn Verse'
    _order = 'sequence, verse_number'

    song_id = fields.Many2one('hymn.song', string='Song',
                              required=True, ondelete='cascade')
    verse_number = fields.Integer(string='Verse #', required=True, default=1)
    text = fields.Text(string='Verse Text (Original)',
                       help='Original script text (Urdu, Punjabi, Arabic, etc.)')
    roman = fields.Text(string='Verse Text (Roman)',
                        help='Roman transliteration for non-native readers')
    sequence = fields.Integer(string='Order', default=10)

    # ── Display helpers ──
    song_title = fields.Char(related='song_id.name', string='Song Title')
    collection_name = fields.Char(related='song_id.collection_id.name',
                                   string='Collection')