# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    """Brute-force protection for the carpenter App PIN login
    (/lifestyle/api/vendor/login) — a 4-6 digit PIN has too little entropy
    to be safe against an unthrottled guessing script."""
    _inherit = 'hr.employee'

    app_pin_failed_attempts = fields.Integer(string='App PIN Failed Attempts', default=0, copy=False)
    app_pin_locked_until = fields.Datetime(string='App PIN Locked Until', copy=False)

    def action_unlock_app_pin(self):
        for employee in self:
            employee.app_pin_failed_attempts = 0
            employee.app_pin_locked_until = False
