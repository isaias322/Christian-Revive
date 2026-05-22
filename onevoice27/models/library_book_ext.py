# -*- coding: utf-8 -*-
from odoo import fields, models, api


class LibraryBookQuizExt(models.Model):
    _inherit = 'library.book'

    quiz_id = fields.Many2one(
        'onevoice.quiz',
        string='Book Quiz',
        ondelete='set null',
        help='Quiz shown to users after reading this book.',
    )

    urdu_version_id = fields.Many2one(
        'library.book',
        string='Urdu Version',
        domain=[['language', '=', 'urdu']],
        ondelete='set null',
        help='Link to the Urdu PDF version of this book. '
             'App will show a language toggle when this is set.',
    )

    @api.model
    def app_get_book_quiz(self, book_id):
        """Return quiz with all questions and options for a given book."""
        book = self.browse(book_id)
        if not book or not book.quiz_id:
            return {}

        quiz = book.quiz_id
        questions = []
        for q in quiz.question_ids.sorted('sequence'):
            options = [
                {
                    'id': opt.id,
                    'text': opt.option_text,
                    'is_correct': opt.is_correct,
                }
                for opt in q.option_ids
            ]
            questions.append({
                'id': q.id,
                'question': q.question_text,
                'type': q.question_type,
                'explanation': q.explanation or '',
                'options': options,
            })

        return {
            'id': quiz.id,
            'name': quiz.name,
            'description': quiz.description or '',
            'shuffle': quiz.shuffle_questions,
            'questions': questions,
        }
