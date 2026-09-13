from odoo import models, fields


class HrEmployeeFinance(models.Model):
    _inherit = 'hr.employee'

    staff_role = fields.Selection(
        selection_add=[('finance_officer', 'Finance Officer')],
        # The base staff_role field (volunteer_and_donation_management)
        # defines no default, so 'set default' isn't valid here — and
        # 'cascade' would delete the employee record entirely. Just clear
        # the role back to unset if church_finance is ever uninstalled.
        ondelete={'finance_officer': lambda recs: recs.write({'staff_role': False})},
    )
