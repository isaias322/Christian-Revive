# -*- coding: utf-8 -*-
{
    'name': 'OneVoice27',
    'version': '1.0.0',
    'category': 'Church Management',
    'summary': 'OneVoice27 — 40-Day Devotionals, Spiritual Preparation, Volunteers, Flashcards & Quizzes',
    'description': """
        OneVoice27 Module
        =================
        - 40-Day Devotional Schedule
        - Spiritual Preparation (Bible Study) tracking
        - OneVoice27 Volunteer Registration
        - Prayer Wall
        - Flashcard Decks & Study Mode (Phase 1)
        - Quizzes — MCQ & True/False (Phase 1)
    """,
    'author': 'Christian Revive',
    'website': 'https://christianrevive.com',
    'depends': ['base', 'volunteer_and_donation_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/onevoice_devotional_views.xml',
        'views/onevoice_bible_study_views.xml',
        'views/onevoice_volunteer_views.xml',
        'views/onevoice_prayer_pledge_views.xml',
        'views/onevoice_prayer_wall_views.xml',
        'views/onevoice_flashcard_views.xml',
        'views/onevoice_quiz_views.xml',
        'views/onevoice_translation_views.xml',
        'views/onevoice_roman_override_views.xml',
        'views/onevoice_baptism_pledge_views.xml',
        'views/onevoice_menu.xml',
        'data/onevoice_devotional_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
