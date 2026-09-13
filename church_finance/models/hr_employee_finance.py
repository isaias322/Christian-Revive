from odoo import models, fields


class HrEmployeeFinance(models.Model):
    _inherit = 'hr.employee'

    staff_role = fields.Selection(
        selection_add=[('finance_officer', 'Finance Officer')],
        ondelete={'finance_officer': 'set default'},
    )
