import logging
from datetime import timedelta
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ChurchAutomationRule(models.Model):
    _name = 'church.automation.rule'
    _description = 'Church Automation Rule'

    name = fields.Char(string='Rule Name', required=True)
    rule_type = fields.Selection([
        ('inactivity', 'Inactivity Alert to Cell Leader'),
        ('pledge_reminder', 'Pledge Due Reminder to Member'),
    ], string='Rule Type', required=True)
    threshold_days = fields.Integer(
        string='Threshold (days)', default=30,
        help='Used by the inactivity rule: how many days without a check-in counts as inactive.')
    is_active = fields.Boolean(string='Active', default=True)
    last_run_at = fields.Datetime(string='Last Run', readonly=True)
    last_run_count = fields.Integer(string='Last Run: Alerts Sent', readonly=True)

    def _notify_member(self, member, title, message):
        self.env['revive.notification'].sudo().create({
            'title': title, 'message': message, 'target': 'all',
            'status': 'sent', 'sent_at': fields.Datetime.now(),
            'target_member_ids': [(6, 0, [member.id])],
        })

    def _run_inactivity(self):
        ResPartner = self.env['res.partner'].sudo()
        sent = 0
        for rule in self.filtered(lambda r: r.rule_type == 'inactivity' and r.is_active):
            cutoff = fields.Datetime.now() - timedelta(days=rule.threshold_days or 30)
            active_ids = self.env['church.event.attendance'].sudo().search([
                ('check_in_time', '>=', cutoff),
            ]).mapped('member_id').ids
            inactive_members = ResPartner.search([
                ('is_member', '=', True), ('id', 'not in', active_ids or [0]),
            ])
            rule_sent = 0
            for member in inactive_members:
                groups = self.env['cell.group'].sudo().search([('member_ids', '=', member.id)])
                for group in groups:
                    if group.leader_id:
                        self._notify_member(
                            group.leader_id,
                            f'Follow-up: {member.name}',
                            f'{member.name} has not attended in over {rule.threshold_days} days. '
                            f'They are in your group "{group.name}" — please reach out.',
                        )
                        rule_sent += 1
            rule.write({'last_run_at': fields.Datetime.now(), 'last_run_count': rule_sent})
            sent += rule_sent
        return sent

    def _run_pledge_reminders(self):
        Pledge = self.env['church.give.pledge'].sudo()
        sent = 0
        for rule in self.filtered(lambda r: r.rule_type == 'pledge_reminder' and r.is_active):
            today = fields.Date.context_today(self)
            due = Pledge.search([
                ('status', '=', 'active'), ('next_reminder_date', '!=', False),
                ('next_reminder_date', '<=', today),
            ])
            rule_sent = 0
            for pledge in due:
                self._notify_member(
                    pledge.member_id,
                    'Pledge Reminder',
                    f'A reminder about your {pledge.frequency.replace("_", " ")} pledge of '
                    f'{pledge.currency} {pledge.pledge_amount:,.0f}. Thank you for your faithfulness.',
                )
                rule_sent += 1
            rule.write({'last_run_at': fields.Datetime.now(), 'last_run_count': rule_sent})
            sent += rule_sent
        return sent

    @api.model
    def _cron_run_all_rules(self):
        rules = self.sudo().search([('is_active', '=', True)])
        inactivity_sent = rules._run_inactivity()
        pledge_sent = rules._run_pledge_reminders()
        _logger.info(
            'Church automation run: %s inactivity alerts, %s pledge reminders',
            inactivity_sent, pledge_sent,
        )
