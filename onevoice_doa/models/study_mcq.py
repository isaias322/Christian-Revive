# -*- coding: utf-8 -*-
from odoo import models, fields


class StudyMcq(models.Model):
    _name        = 'onevoice.study.mcq'
    _description = 'Chapter MCQ'
    _order       = 'chapter_id, sequence'

    chapter_id     = fields.Many2one('onevoice.doa.chapter', string='Chapter',
                                     required=True, ondelete='cascade')
    book_id        = fields.Many2one('onevoice.study.book',
                                     related='chapter_id.book_id',
                                     store=True, string='Book')
    sequence       = fields.Integer(string='Order', default=10)
    is_published   = fields.Boolean(string='Published', default=True)

    question_en    = fields.Char(string='Question (EN)', required=True)
    question_ur    = fields.Char(string='Question (UR)')

    option_a_en    = fields.Char(string='Option A (EN)', required=True)
    option_b_en    = fields.Char(string='Option B (EN)', required=True)
    option_c_en    = fields.Char(string='Option C (EN)')
    option_d_en    = fields.Char(string='Option D (EN)')

    option_a_ur    = fields.Char(string='Option A (UR)')
    option_b_ur    = fields.Char(string='Option B (UR)')
    option_c_ur    = fields.Char(string='Option C (UR)')
    option_d_ur    = fields.Char(string='Option D (UR)')

    correct_option = fields.Selection([
        ('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D'),
    ], string='Correct Answer', required=True, default='a')

    explanation_en       = fields.Text(string='Explanation (EN)')
    explanation_ur       = fields.Text(string='Explanation (UR)')
    show_on_wrong        = fields.Boolean(string='Show on Wrong Answer', default=True)
    show_on_correct      = fields.Boolean(string='Show on Correct Answer', default=False)
