# -*- coding: utf-8 -*-
from odoo import api, fields, models


class OneVoiceBaptismPledge(models.Model):
    _name = 'onevoice.baptism.pledge'
    _description = 'One Voice 27 Baptism Pledge'
    _order = 'create_date desc'

    # ── Step 1: Candidate Info ─────────────────────────────────────────────
    first_name = fields.Char('First Name', required=True)
    middle_name = fields.Char('Middle Name')
    last_name = fields.Char('Last Name', required=True)
    date_of_birth = fields.Date('Date of Birth', required=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('prefer_not', 'Prefer not to say'),
    ], string='Gender', required=True)
    street = fields.Char('Street Address')
    city = fields.Char('City')
    state_province = fields.Char('State / Province')
    zip_code = fields.Char('Zip / Postal Code')
    phone = fields.Char('Phone')
    email = fields.Char('Email')
    occupation_or_grade = fields.Char('Occupation / School Grade')

    # ── Step 2: Spiritual Journey ──────────────────────────────────────────
    salvation_date = fields.Date('Date of Salvation / Conversion')
    conversion_experience = fields.Text('Describe Your Salvation Experience')
    completed_bible_studies = fields.Boolean('Completed OneVoice Bible Studies?')
    study_conductor = fields.Char('Bible Study Conductor Name')
    study_duration_value = fields.Integer('Study Duration (value)')
    study_duration_unit = fields.Selection([
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string='Study Duration Unit', default='weeks')
    attended_evangelistic_series = fields.Boolean('Attended Evangelistic Series?')
    evangelistic_series_details = fields.Char('Evangelistic Series Details')

    # ── Step 3: 13 SDA Vows ───────────────────────────────────────────────
    vow_accept_bible = fields.Boolean('1. Accept the Bible as God\'s inspired Word and the only rule of faith and practice')
    vow_one_god = fields.Boolean('2. Believe in God the Father, His Son Jesus Christ, and the Holy Spirit')
    vow_ten_commandments = fields.Boolean('3. Accept and keep the Ten Commandments as a transcript of God\'s character')
    vow_sabbath = fields.Boolean('4. Keep the seventh-day Sabbath holy as God\'s perpetual sign of His sanctifying power')
    vow_second_coming = fields.Boolean('5. Accept the doctrine of the Second Coming of Christ')
    vow_death_state = fields.Boolean('6. Believe in the biblical teaching of the state of the dead')
    vow_baptism = fields.Boolean('7. Accept baptism by immersion as a condition of church membership')
    vow_health = fields.Boolean('8. Accept the SDA teaching on health reform and practice a healthy lifestyle')
    vow_tithe = fields.Boolean('9. Return a faithful tithe and give offerings to support God\'s work')
    vow_spiritual_gifts = fields.Boolean('10. Believe in spiritual gifts including the gift of prophecy manifested in the remnant church')
    vow_remnant_church = fields.Boolean('11. Believe in the remnant church and support its worldwide mission')
    vow_unity = fields.Boolean('12. Accept the Christian standards of dress, adornment, and conduct')
    vow_readiness = fields.Boolean('13. Commit to preparing yourself and others for Christ\'s soon return')

    # ── Step 4: Lifestyle Commitments ─────────────────────────────────────
    lifestyle_holy_spirit_temple = fields.Boolean('Honor body as temple of the Holy Spirit')
    lifestyle_no_alcohol = fields.Boolean('Abstain from alcohol')
    lifestyle_no_tobacco = fields.Boolean('Abstain from tobacco')
    lifestyle_no_drugs = fields.Boolean('Abstain from illegal drugs')
    lifestyle_clean_foods = fields.Boolean('Follow biblically clean foods')
    lifestyle_sabbath = fields.Boolean('Observe the Sabbath faithfully')
    lifestyle_stewardship = fields.Boolean('Practice stewardship and tithe')
    lifestyle_prayer_bible = fields.Boolean('Commit to daily prayer and Bible study')

    # ── Step 5: Ceremony Details ───────────────────────────────────────────
    preferred_location = fields.Char('Preferred Church / Location')
    preferred_date = fields.Date('Preferred Baptism Date')
    consent_statement_true = fields.Boolean('I confirm all information is true and accurate')
    consent_pastoral_contact = fields.Boolean('I consent to be contacted by pastoral team')
    consent_ceremony_photo = fields.Boolean('I consent to photos/video at the ceremony')
    consent_membership = fields.Boolean('I wish to become a member of the Seventh-day Adventist Church')

    # ── Photo ─────────────────────────────────────────────────────────────
    photo = fields.Binary('Candidate Photo', attachment=True)

    # ── Link to Spiritual Prep contact ────────────────────────────────────
    study_contact_id = fields.Integer('Study Contact ID', index=True, default=0)

    # ── Metadata ──────────────────────────────────────────────────────────
    device_id = fields.Char('Device ID')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
    ], string='Status', default='draft', required=True)
    approval_date = fields.Date('Approval Date', readonly=True)

    # ── Computed ──────────────────────────────────────────────────────────
    full_name = fields.Char('Full Name', compute='_compute_full_name', store=True)

    @api.depends('first_name', 'middle_name', 'last_name')
    def _compute_full_name(self):
        for r in self:
            parts = [r.first_name, r.middle_name, r.last_name]
            r.full_name = ' '.join(p for p in parts if p)

    # ── Admin actions ─────────────────────────────────────────────────────
    def action_approve(self):
        for r in self:
            if r.status == 'submitted':
                r.status = 'approved'
                r.approval_date = fields.Date.today()

    def action_reset_draft(self):
        for r in self:
            r.status = 'draft'

    # ── App API ───────────────────────────────────────────────────────────
    @api.model
    def app_submit_baptism_pledge(self, vals, record_id=None):
        """Create or update a baptism pledge record from the Flutter app.

        Enforces one-pledge-per-device: if no record_id is provided but vals
        contains a device_id, we search for an existing record first so a
        reinstall or cleared-prefs cannot produce a duplicate.
        """
        # Safety: older app versions may pass record_id inside vals dict
        if not record_id:
            record_id = vals.pop('record_id', None)
        else:
            vals.pop('record_id', None)  # ensure record_id never reaches write()

        # Coerce boolean strings
        bool_fields = [
            'completed_bible_studies', 'attended_evangelistic_series',
            'vow_accept_bible', 'vow_one_god', 'vow_ten_commandments',
            'vow_sabbath', 'vow_second_coming', 'vow_death_state',
            'vow_baptism', 'vow_health', 'vow_tithe', 'vow_spiritual_gifts',
            'vow_remnant_church', 'vow_unity', 'vow_readiness',
            'lifestyle_holy_spirit_temple', 'lifestyle_no_alcohol',
            'lifestyle_no_tobacco', 'lifestyle_no_drugs', 'lifestyle_clean_foods',
            'lifestyle_sabbath', 'lifestyle_stewardship', 'lifestyle_prayer_bible',
            'consent_statement_true', 'consent_pastoral_contact',
            'consent_ceremony_photo', 'consent_membership',
        ]
        for f in bool_fields:
            if f in vals:
                v = vals[f]
                if isinstance(v, str):
                    vals[f] = v.lower() in ('true', '1', 'yes')

        # Convert empty strings to False for Date and Binary fields so ORM
        # does not reject the write (Odoo Date/Binary reject '' but accept False)
        for f in ('date_of_birth', 'salvation_date', 'preferred_date', 'approval_date'):
            if vals.get(f) == '':
                vals[f] = False
        if vals.get('photo') == '':
            vals.pop('photo')  # omit rather than clear existing photo

        # Explicit record_id → update
        if record_id:
            record = self.browse(int(record_id))
            if record.exists():
                record.write(vals)
                return {'id': record.id, 'status': record.status}

        # No record_id → check study_contact_id first (one pledge per contact)
        contact_id = vals.get('study_contact_id', 0)
        if contact_id:
            existing = self.search([('study_contact_id', '=', int(contact_id))], limit=1)
            if existing:
                existing.write(vals)
                return {'id': existing.id, 'status': existing.status}

        # Fallback: check device_id only for legacy records that have no contact linked.
        # Must NOT match records that belong to a different contact on the same device.
        device_id = vals.get('device_id', '').strip()
        if device_id:
            existing = self.search([
                ('device_id', '=', device_id),
                ('study_contact_id', '=', 0),
            ], limit=1)
            if existing:
                existing.write(vals)
                return {'id': existing.id, 'status': existing.status}

        record = self.create(vals)
        return {'id': record.id, 'status': record.status}

    @api.model
    def app_get_pledge_by_contact(self, contact_id):
        """Return the pledge for a given study contact ID, or {} if none exists."""
        if not contact_id:
            return {}
        record = self.search([('study_contact_id', '=', int(contact_id))], limit=1)
        if not record:
            return {}
        return self.app_get_baptism_pledge(record.id)

    @api.model
    def app_get_pledges_summary(self, contact_ids):
        """Return {contact_id: status} for a list of contact IDs."""
        if not contact_ids:
            return {}
        records = self.search_read(
            [('study_contact_id', 'in', contact_ids)],
            ['study_contact_id', 'status'],
        )
        return {r['study_contact_id']: r['status'] for r in records}

    @api.model
    def app_get_baptism_pledge(self, record_id):
        """Return a single baptism pledge record as a flat dict for the Flutter app."""
        record = self.browse(record_id)
        if not record.exists():
            return {}
        return {
            'id': record.id,
            'status': record.status,
            # Step 1
            'first_name': record.first_name or '',
            'middle_name': record.middle_name or '',
            'last_name': record.last_name or '',
            'date_of_birth': str(record.date_of_birth) if record.date_of_birth else '',
            'gender': record.gender or '',
            'street': record.street or '',
            'city': record.city or '',
            'state_province': record.state_province or '',
            'zip_code': record.zip_code or '',
            'phone': record.phone or '',
            'email': record.email or '',
            'occupation_or_grade': record.occupation_or_grade or '',
            # Step 2
            'salvation_date': str(record.salvation_date) if record.salvation_date else '',
            'conversion_experience': record.conversion_experience or '',
            'completed_bible_studies': record.completed_bible_studies,
            'study_conductor': record.study_conductor or '',
            'study_duration_value': record.study_duration_value or 0,
            'study_duration_unit': record.study_duration_unit or 'weeks',
            'attended_evangelistic_series': record.attended_evangelistic_series,
            'evangelistic_series_details': record.evangelistic_series_details or '',
            # Step 3
            'vow_accept_bible': record.vow_accept_bible,
            'vow_one_god': record.vow_one_god,
            'vow_ten_commandments': record.vow_ten_commandments,
            'vow_sabbath': record.vow_sabbath,
            'vow_second_coming': record.vow_second_coming,
            'vow_death_state': record.vow_death_state,
            'vow_baptism': record.vow_baptism,
            'vow_health': record.vow_health,
            'vow_tithe': record.vow_tithe,
            'vow_spiritual_gifts': record.vow_spiritual_gifts,
            'vow_remnant_church': record.vow_remnant_church,
            'vow_unity': record.vow_unity,
            'vow_readiness': record.vow_readiness,
            # Step 4
            'lifestyle_holy_spirit_temple': record.lifestyle_holy_spirit_temple,
            'lifestyle_no_alcohol': record.lifestyle_no_alcohol,
            'lifestyle_no_tobacco': record.lifestyle_no_tobacco,
            'lifestyle_no_drugs': record.lifestyle_no_drugs,
            'lifestyle_clean_foods': record.lifestyle_clean_foods,
            'lifestyle_sabbath': record.lifestyle_sabbath,
            'lifestyle_stewardship': record.lifestyle_stewardship,
            'lifestyle_prayer_bible': record.lifestyle_prayer_bible,
            # Meta
            'approval_date': str(record.approval_date) if record.approval_date else '',
            # Photo
            'photo': record.photo.decode('utf-8') if record.photo else '',
            # Step 5
            'preferred_location': record.preferred_location or '',
            'preferred_date': str(record.preferred_date) if record.preferred_date else '',
            'consent_statement_true': record.consent_statement_true,
            'consent_pastoral_contact': record.consent_pastoral_contact,
            'consent_ceremony_photo': record.consent_ceremony_photo,
            'consent_membership': record.consent_membership,
        }
