from odoo import models, fields, api
from odoo.exceptions import AccessError


class OneVoiceBibleStudy(models.Model):
    _name = 'onevoice.bible.study'
    _description = 'OneVoice27 Bible Study Registration'
    _order = 'create_date desc'
    _rec_name = 'contact_name'

    contact_name = fields.Char(string='Contact Name', required=True)

    # ── Ownership: which Odoo user created this record ──────────
    owner_uid = fields.Integer(
        string='Owner UID',
        default=lambda self: self.env.uid,
        index=True,
    )

    # ── session_key: device identifier sent from the app ────────
    # If this column is missing in your DB, run the migration SQL below.
    session_key = fields.Char(string='Session Key', index=True)
    email       = fields.Char(string='Email')
    church_name = fields.Char(string='Church Name')

    phone = fields.Char(string='Phone')
    location = fields.Char(string='Location / City')
    study_days = fields.Char(string='Study Days')
    state = fields.Selection([
        ('interested', 'Interested'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='Status', default='interested', required=True)
    notes = fields.Text(string='Notes')
    partner_id = fields.Many2one('res.partner', string='Related Contact')
    completed_session_count = fields.Integer(string='Completed Sessions', default=0)
    completed_session_ids = fields.Text(string='Completed Session IDs')
    total_session_count = fields.Integer(string='Total Sessions', default=121)
    certificate_eligible = fields.Boolean(
        string='Certificate Eligible',
        compute='_compute_certificate_eligible',
        store=True,
    )
    certificate_issued = fields.Boolean(string='Certificate Issued', default=False)
    certificate_issued_date = fields.Datetime(string='Certificate Issued On')
    prayer_pledge_count = fields.Integer(string='Prayer Pledges', default=0)
    testimony_count = fields.Integer(string='Testimonies', default=0)
    prayer_pledges_details = fields.Text(string='Prayer Pledge Details')
    testimonies_details = fields.Text(string='Testimony Details')

    # ── Certificate eligibility ──────────────────────────────────

    @api.depends('completed_session_count', 'total_session_count')
    def _compute_certificate_eligible(self):
        for record in self:
            record.certificate_eligible = (
                record.total_session_count > 0
                and record.completed_session_count >= record.total_session_count
            )

    # ── Helper: is the calling user an Odoo admin? ───────────────

    def _caller_is_admin(self):
        """Return True if the RPC caller has Settings (base.group_system) rights."""
        return self.env.user.has_group('base.group_system')

    # ────────────────────────────────────────────────────────────
    # App-facing API methods (called via JSON-RPC / XML-RPC)
    # All methods use sudo() internally but enforce owner_uid so
    # each app user only sees / touches their own records.
    # Admins (group_system) can see everything.
    # ────────────────────────────────────────────────────────────

    @api.model
    def app_search_registrations(self, session_key):
        """
        Return only registrations that belong to this session_key.
        Admin access to all records is via the Odoo web UI, not this endpoint.
        """
        if not session_key:
            return []

        records = self.sudo().search(
            [('session_key', '=', session_key)],
            order='create_date desc',
        )
        return [self._format_record(r) for r in records]

    @api.model
    def app_create_registration(self, vals):
        """
        Create a new registration.  session_key is stored so the device
        can retrieve it later.  owner_uid is set to the calling user.
        Falls back gracefully if session_key column is missing (prints
        a clear error rather than crashing silently).
        """
        # Ensure ownership fields are always set
        vals.setdefault('owner_uid', self.env.uid)

        record = self.sudo().create(vals)
        return self._format_record(record)

    @api.model
    def app_update_progress(self, record_id, session_key,
                            completed_sessions, total_sessions,
                            completed_session_ids, certificate_issued=False):
        """
        Update study progress.  Only the owner (matching session_key) or
        an admin may update a record.
        """
        record = self._get_own_record(record_id, session_key)
        if record is None:
            return {'error': 'Record not found or access denied'}

        vals = {
            'completed_session_count': completed_sessions,
            'total_session_count': total_sessions,
            'completed_session_ids': ','.join(completed_session_ids)
            if isinstance(completed_session_ids, list)
            else (completed_session_ids or ''),
        }
        if certificate_issued:
            vals['certificate_issued'] = True
            vals['certificate_issued_date'] = fields.Datetime.now()

        record.write(vals)
        return {'success': True, 'id': record.id}

    @api.model
    def app_update_registration(self, record_id, session_key, vals):
        """Update contact info fields (name, phone, email, church, location). Owner only."""
        record = self._get_own_record(record_id, session_key)
        if record is None:
            return {'error': 'Record not found or access denied'}
        allowed = {'name', 'phone', 'email', 'church_name', 'location'}
        clean = {k: v for k, v in vals.items() if k in allowed}
        if clean:
            record.write(clean)
        return {'success': True, 'id': record.id}

    @api.model
    def app_update_pledge_testimony_count(self, record_id, prayer_pledge_count,
                                          testimony_count,
                                          prayer_pledges_details=None,
                                          testimonies_details=None,
                                          session_key=None):
        """
        Update pledge / testimony counts.  Owner or admin only.
        session_key is optional but recommended for extra verification.
        """
        record = self._get_own_record(record_id, session_key)
        if record is None:
            return {'error': 'Record not found or access denied'}

        vals = {
            'prayer_pledge_count': prayer_pledge_count,
            'testimony_count': testimony_count,
        }
        if prayer_pledges_details is not None:
            vals['prayer_pledges_details'] = prayer_pledges_details
        if testimonies_details is not None:
            vals['testimonies_details'] = testimonies_details
        record.write(vals)
        return {'success': True, 'id': record.id}

    @api.model
    def app_delete_registration(self, record_id, session_key):
        """
        Delete a registration. Owner or admin only.
        """
        record = self._get_own_record(record_id, session_key)
        if record is None:
            return {'error': 'Record not found or access denied'}
        record.unlink()
        return {'success': True}

    # ── Internal helpers ─────────────────────────────────────────

    def _get_own_record(self, record_id, session_key=None):
        """
        Return the record if the caller owns it (matching session_key or
        owner_uid) OR if the caller is an admin.  Returns None otherwise.
        """
        record = self.sudo().browse(record_id)
        if not record.exists():
            return None
        if self._caller_is_admin():
            return record
        # Match by session_key (device) or owner_uid (Odoo user)
        if session_key and record.session_key == session_key:
            return record
        if record.owner_uid == self.env.uid:
            return record
        return None

    def _format_record(self, r):
        """Serialize a record to a dict the Flutter app can consume."""
        raw_ids = r.completed_session_ids or ''
        completed_ids = [s for s in raw_ids.split(',') if s.strip()]
        return {
            'id': r.id,
            'name': r.contact_name,
            'email': r.email or '',
            'church_name': r.church_name or '',
            'phone': r.phone or '',
            'location': r.location or '',
            'completedSessionCount': r.completed_session_count,
            'completedSessionIds': completed_ids,
            'totalSessionCount': r.total_session_count,
            'certificateEligible': r.certificate_eligible,
            'certificateIssued': r.certificate_issued,
            'prayerPledgeCount': r.prayer_pledge_count,
            'testimonyCount': r.testimony_count,
            'sessionKey': r.session_key or '',
        }

    # ── Standard Odoo UI actions ─────────────────────────────────

    def action_set_interested(self):
        self.write({'state': 'interested'})

    def action_set_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_set_completed(self):
        self.write({'state': 'completed'})

    def action_mark_certificate_issued(self):
        self.write({
            'certificate_issued': True,
            'certificate_issued_date': fields.Datetime.now(),
        })