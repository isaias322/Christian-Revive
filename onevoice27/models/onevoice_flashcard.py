# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OnevoiceFlashcardDeck(models.Model):
    _name = 'onevoice.flashcard.deck'
    _description = 'Flashcard Deck'
    _order = 'sequence, name'

    name          = fields.Char(string='Deck Name', required=True)
    description   = fields.Text(string='Description')
    is_active     = fields.Boolean(string='Active', default=True)
    sequence      = fields.Integer(string='Sequence', default=10)
    card_ids      = fields.One2many('onevoice.flashcard', 'deck_id', string='Cards')
    card_count    = fields.Integer(string='Card Count', compute='_compute_card_count', store=False)
    attempt_count = fields.Integer(string='Study Sessions', compute='_compute_attempt_count', store=False)

    @api.depends('card_ids')
    def _compute_card_count(self):
        for deck in self:
            deck.card_count = len(deck.card_ids)

    @api.depends()
    def _compute_attempt_count(self):
        for deck in self:
            deck.attempt_count = self.env['onevoice.flashcard.attempt'].search_count(
                [('deck_id', '=', deck.id)]
            )

    @api.model
    def app_get_decks(self):
        """Return all active decks for the Flutter app."""
        decks = self.sudo().search([('is_active', '=', True)], order='sequence asc')
        return [
            {
                'id':            d.id,
                'name':          d.name or '',
                'description':   d.description or '',
                'card_count':    d.card_count,
                'attempt_count': d.attempt_count,
            }
            for d in decks
        ]


class OnevoiceFlashcard(models.Model):
    _name = 'onevoice.flashcard'
    _description = 'Flashcard'
    _order = 'deck_id, sequence'

    deck_id    = fields.Many2one('onevoice.flashcard.deck', string='Deck', required=True, ondelete='cascade')
    front_text = fields.Text(string='Front (Question)', required=True)
    back_text  = fields.Text(string='Back (Answer)', required=True)
    hint       = fields.Char(string='Hint')
    sequence   = fields.Integer(string='Sequence', default=10)
    image      = fields.Image(string='Card Image', max_width=800, max_height=800)

    @api.model
    def app_get_cards(self, deck_id):
        """Return all cards for a deck for the Flutter app."""
        cards = self.sudo().search([('deck_id', '=', int(deck_id))], order='sequence asc')
        return [
            {
                'id':      c.id,
                'deck_id': c.deck_id.id,
                'front':   c.front_text or '',
                'back':    c.back_text or '',
                'hint':    c.hint or '',
                'image':   c.image.decode('utf-8') if c.image else '',
            }
            for c in cards
        ]


class OnevoiceFlashcardAttempt(models.Model):
    _name = 'onevoice.flashcard.attempt'
    _description = 'Flashcard Deck Study Session'
    _order = 'completed_at desc'

    deck_id      = fields.Many2one('onevoice.flashcard.deck', string='Deck', ondelete='set null')
    user_name    = fields.Char(string='User Name')
    completed_at = fields.Datetime(string='Studied At')

    @api.model
    def app_log_attempt(self, vals):
        """Log a completed deck study session from the Flutter app."""
        self.sudo().create({
            'deck_id':      vals.get('deck_id'),
            'user_name':    vals.get('user_name', ''),
            'completed_at': fields.Datetime.now(),
        })
        return True
