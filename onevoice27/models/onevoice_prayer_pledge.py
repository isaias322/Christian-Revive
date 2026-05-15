# -*- coding: utf-8 -*-
from odoo import models, fields, api


class OneVoicePrayerPledge(models.Model):
    _name        = 'onevoice.prayer.pledge'
    _description = 'Prayer Pledge'
    _order       = 'posted_date desc'

    pledge_name     = fields.Char(string='Name', required=True)
    prayer_focus    = fields.Char(string='Prayer Focus')
    prayer_duration = fields.Char(string='Duration')
    posted_date     = fields.Datetime(string='Submitted', default=fields.Datetime.now)
    source_key      = fields.Char(string='Session Key')
    admin_response  = fields.Text(string='Admin Response / Kind Words')

    # ── App API ──────────────────────────────────────────────────

    @api.model
    def app_submit_pledge(self, vals):
        """Create a prayer pledge from the Flutter app."""
        record = self.sudo().create({
            'pledge_name':     vals.get('name', ''),
            'prayer_focus':    vals.get('focus', ''),
            'prayer_duration': vals.get('duration', ''),
            'posted_date':     fields.Datetime.now(),
            'source_key':      vals.get('session_key', ''),
        })
        return {'id': record.id, 'success': True}

    @api.model
    def app_get_my_pledges(self, session_key):
        """Return pledges belonging to this device session only."""
        if not session_key:
            return []
        pledges = self.sudo().search(
            [('source_key', '=', session_key)],
            order='posted_date desc',
        )
        return [
            {
                'id':             p.id,
                'name':           p.pledge_name or '',
                'focus':          p.prayer_focus or '',
                'duration':       p.prayer_duration or '',
                'date':           p.posted_date.isoformat() if p.posted_date else '',
                'admin_response': p.admin_response or '',
            }
            for p in pledges
        ]

    def action_delete_pledge(self):
        """Admin button: delete this pledge and return to the list."""
        self.ensure_one()
        self.unlink()
        return {
            'type':    'ir.actions.act_window',
            'name':    'Prayer Pledges',
            'res_model': 'onevoice.prayer.pledge',
            'view_mode': 'list,form',
            'target':  'current',
        }

    @api.model
    def app_delete_pledge(self, pledge_id, session_key):
        """Delete a pledge — only if it belongs to this session."""
        record = self.sudo().search([
            ('id',         '=', int(pledge_id)),
            ('source_key', '=', session_key),
        ], limit=1)
        if record:
            record.unlink()
            return True
        return False
