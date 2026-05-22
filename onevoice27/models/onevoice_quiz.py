# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OnevoiceQuiz(models.Model):
    _name = 'onevoice.quiz'
    _description = 'Quiz'
    _order = 'name'

    name               = fields.Char(string='Quiz Name', required=True)
    description        = fields.Text(string='Description')
    is_active          = fields.Boolean(string='Active', default=True)
    shuffle_questions  = fields.Boolean(string='Shuffle Questions', default=False)
    question_ids       = fields.One2many('onevoice.quiz.question', 'quiz_id', string='Questions')
    question_count     = fields.Integer(string='Questions', compute='_compute_question_count', store=False)
    attempt_count      = fields.Integer(string='Attempts', compute='_compute_attempt_count', store=False)

    @api.depends('question_ids')
    def _compute_question_count(self):
        for quiz in self:
            quiz.question_count = len(quiz.question_ids)

    @api.depends()
    def _compute_attempt_count(self):
        for quiz in self:
            quiz.attempt_count = self.env['onevoice.quiz.attempt'].search_count(
                [('quiz_id', '=', quiz.id)]
            )

    @api.model
    def app_get_quizzes(self):
        """Return all active quizzes for the Flutter app."""
        quizzes = self.sudo().search([('is_active', '=', True)])
        return [
            {
                'id':             q.id,
                'name':           q.name or '',
                'description':    q.description or '',
                'question_count': q.question_count,
                'shuffle':        q.shuffle_questions,
            }
            for q in quizzes
        ]

    @api.model
    def app_get_quiz(self, quiz_id):
        """Return a quiz with all questions and options for the Flutter app."""
        quiz = self.sudo().browse(int(quiz_id))
        if not quiz.exists():
            return {}
        questions = []
        for q in quiz.question_ids.sorted('sequence'):
            options = [
                {
                    'id':         o.id,
                    'text':       o.option_text or '',
                    'is_correct': o.is_correct,
                }
                for o in q.option_ids
            ]
            questions.append({
                'id':          q.id,
                'type':        q.question_type,
                'text':        q.question_text or '',
                'explanation': q.explanation or '',
                'image':       q.image.decode('utf-8') if q.image else '',
                'options':     options,
            })
        return {
            'id':          quiz.id,
            'name':        quiz.name or '',
            'description': quiz.description or '',
            'shuffle':     quiz.shuffle_questions,
            'questions':   questions,
        }


class OnevoiceQuizQuestion(models.Model):
    _name = 'onevoice.quiz.question'
    _description = 'Quiz Question'
    _order = 'quiz_id, sequence'

    quiz_id       = fields.Many2one('onevoice.quiz', string='Quiz', required=True, ondelete='cascade')
    question_type = fields.Selection([
        ('mcq',        'Multiple Choice'),
        ('true_false', 'True / False'),
    ], string='Question Type', default='mcq', required=True)
    question_text = fields.Text(string='Question', required=True)
    explanation   = fields.Text(string='Explanation')
    image         = fields.Image(string='Question Image', max_width=800, max_height=800)
    sequence      = fields.Integer(string='Sequence', default=10)
    option_ids    = fields.One2many('onevoice.quiz.option', 'question_id', string='Options')


class OnevoiceQuizOption(models.Model):
    _name = 'onevoice.quiz.option'
    _description = 'Quiz Option'

    question_id = fields.Many2one('onevoice.quiz.question', string='Question',
                                  required=True, ondelete='cascade')
    option_text = fields.Char(string='Option Text', required=True)
    is_correct  = fields.Boolean(string='Correct Answer', default=False)


class OnevoiceQuizAttempt(models.Model):
    _name = 'onevoice.quiz.attempt'
    _description = 'Quiz Attempt'
    _order = 'completed_at desc'

    quiz_id         = fields.Many2one('onevoice.quiz', string='Quiz')
    user_name       = fields.Char(string='User Name')
    score           = fields.Integer(string='Score', default=0)
    total_questions = fields.Integer(string='Total Questions', default=0)
    score_percent   = fields.Integer(string='Score %', compute='_compute_score_percent', store=True)
    passed          = fields.Boolean(string='Passed', compute='_compute_score_percent', store=True)
    completed_at    = fields.Datetime(string='Completed At')
    retake_count    = fields.Integer(string='Retakes', default=0)
    app_session_key = fields.Char(string='Session Key')

    @api.depends('score', 'total_questions')
    def _compute_score_percent(self):
        for attempt in self:
            if attempt.total_questions:
                attempt.score_percent = round(attempt.score * 100 / attempt.total_questions)
            else:
                attempt.score_percent = 0
            attempt.passed = attempt.score_percent >= 60

    @api.model
    def app_submit_attempt(self, vals):
        """Create or update a quiz attempt. Retakes update the existing row."""
        quiz_id   = vals.get('quiz_id')
        user_name = vals.get('user_name', '')
        existing  = self.sudo().search([
            ('quiz_id',   '=', quiz_id),
            ('user_name', '=', user_name),
        ], limit=1)
        if existing:
            existing.write({
                'score':           vals.get('score', 0),
                'total_questions': vals.get('total_questions', 0),
                'completed_at':    fields.Datetime.now(),
                'retake_count':    existing.retake_count + 1,
            })
            record = existing
        else:
            record = self.sudo().create({
                'quiz_id':         quiz_id,
                'user_name':       user_name,
                'score':           vals.get('score', 0),
                'total_questions': vals.get('total_questions', 0),
                'completed_at':    fields.Datetime.now(),
                'retake_count':    0,
                'app_session_key': vals.get('session_key', ''),
            })
        return {
            'id':              record.id,
            'score':           record.score,
            'total_questions': record.total_questions,
        }
