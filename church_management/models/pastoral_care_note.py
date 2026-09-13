from odoo import models, fields, api


class PastoralCareNote(models.Model):
    _name = 'pastoral.care.note'
    _description = 'Pastoral Care Note'
    _order = 'date desc'

    # SECURITY NOTE: this note's `content` is sensitive (counseling/prayer
    # records) and access below is strictly scoped in Python to the
    # author and senior pastors/admins — nobody else can reach it through
    # the app_* RPC layer. It is NOT yet encrypted at rest in Postgres
    # (that needs pgcrypto or a Python crypto lib added to Dockerfile.odoo,
    # which isn't currently installed — an infra change, not a code change,
    # left for a deliberate follow-up rather than made silently here).

    member_id = fields.Many2one(
        'res.partner', string='Member', required=True,
        domain=[('is_member', '=', True)],
    )
    author_id = fields.Many2one(
        'hr.employee', string='Author', required=True,
        domain=[('staff_role', '=', 'pastor')],
    )
    note_type = fields.Selection([
        ('visit', 'Home Visit'),
        ('call', 'Phone Call'),
        ('counseling', 'Counseling Session'),
        ('prayer', 'Prayer Request'),
        ('other', 'Other'),
    ], string='Type', default='visit', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    content = fields.Text(string='Notes', required=True)
    follow_up_date = fields.Date(string='Follow-up Date')
    visible_to_senior_pastor_only = fields.Boolean(
        string='Restrict to Author + Senior Pastor', default=True,
        help='If off, any pastor with access to this member can read the note.',
    )

    # ── Church Management RPC (Phase 2) ─────────────────────────

    def _pastoral_access(self, requester_staff_id):
        """(employee, is_senior_or_admin) for the calling staff member, or
        (None, False) if requester_staff_id doesn't resolve to live staff."""
        if not requester_staff_id:
            return None, False
        employee = self.env['hr.employee'].sudo().browse(requester_staff_id)
        if not employee.exists() or not employee.is_app_active:
            return None, False
        is_senior_or_admin = employee.staff_role == 'admin' or (
            employee.staff_role == 'pastor' and employee.is_senior_pastor
        )
        return employee, is_senior_or_admin

    @api.model
    def app_get_pastoral_notes(self, member_id, requester_staff_id=None):
        employee, is_senior_or_admin = self._pastoral_access(requester_staff_id)
        if not employee or employee.staff_role not in ('pastor', 'admin'):
            return {'success': False, 'error': 'Not authorized'}

        domain = [('member_id', '=', member_id)]
        if not is_senior_or_admin:
            # An associate pastor only sees their own notes, plus any note
            # another pastor explicitly opened up beyond author-only.
            domain += ['|', ('author_id', '=', employee.id),
                       ('visible_to_senior_pastor_only', '=', False)]

        notes = self.sudo().search(domain, order='date desc')
        return {'success': True, 'notes': notes.read([
            'id', 'note_type', 'date', 'content', 'follow_up_date',
            'author_id', 'visible_to_senior_pastor_only',
        ])}

    @api.model
    def app_add_pastoral_note(self, member_id, vals, requester_staff_id=None):
        employee, _is_senior = self._pastoral_access(requester_staff_id)
        if not employee or employee.staff_role not in ('pastor', 'admin'):
            return {'success': False, 'error': 'Not authorized'}

        vals = dict(vals or {})
        vals['member_id'] = member_id
        vals['author_id'] = employee.id
        note = self.sudo().create(vals)
        return {'success': True, 'note_id': note.id}

    @api.model
    def app_get_my_follow_ups(self, requester_staff_id):
        employee, is_senior_or_admin = self._pastoral_access(requester_staff_id)
        if not employee or employee.staff_role not in ('pastor', 'admin'):
            return {'success': False, 'error': 'Not authorized'}

        domain = [('follow_up_date', '!=', False), ('follow_up_date', '<=', fields.Date.context_today(self))]
        if not is_senior_or_admin:
            domain.append(('author_id', '=', employee.id))

        notes = self.sudo().search(domain, order='follow_up_date')
        return {'success': True, 'follow_ups': notes.read([
            'id', 'member_id', 'note_type', 'follow_up_date', 'content',
        ])}
