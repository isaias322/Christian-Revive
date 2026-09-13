{
    'name': 'Church Communication',
    'version': '1.0.0',
    'category': 'Church',
    'summary': 'Segmented bulk messaging, automation rules, branches and GDPR tools for Christian Revive',
    'description': """
        Christian Revive - Church Communication
        =========================================
        - Bulk messages to member segments (all / a cell group / inactive /
          birthday today / overdue pledge), shown in the existing in-app
          notification feed and, for the "all members" segment, also pushed
          via the existing FCM broadcast (revive.notification)
        - Automation rules: inactivity alerts to the member's cell leader,
          pledge-due reminders to the member — run on a daily cron
        - Lightweight multi-branch tagging (church.branch + branch_id on
          members/cell groups) — foundation only; RBAC scoping in
          church_management is not yet branch-aware, by design (this
          congregation runs single-branch today; wiring full isolation is
          a follow-up once a second branch actually exists)
        - GDPR: a member can export their own data, or request anonymization
          (financial totals are preserved, PII is scrubbed)
        - API endpoints for the Flutter mobile app
    """,
    'author': 'Christian Revive',
    'website': 'https://christianrevive.com',
    'depends': ['base', 'volunteer_and_donation_management', 'church_management', 'church_finance'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/church_branch_views.xml',
        'views/bulk_message_views.xml',
        'views/automation_rule_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'sequence': 18,
}
