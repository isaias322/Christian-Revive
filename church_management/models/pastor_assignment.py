from odoo import models, fields


class HrEmployeeSeniorPastor(models.Model):
    _inherit = 'hr.employee'

    is_senior_pastor = fields.Boolean(
        string='Senior Pastor',
        help='Senior pastors see every member in the church. '
             'Associate/assistant pastors see only members explicitly '
             'assigned to them under Church Management > Pastor Assignments.',
    )


class PastorAssignment(models.Model):
    _name = 'pastor.assignment'
    _description = 'Pastor to Member Assignment'
    _order = 'pastor_id, member_id'
    _rec_name = 'member_id'

    pastor_id = fields.Many2one(
        'hr.employee', string='Pastor', required=True,
        domain=[('staff_role', '=', 'pastor')],
    )
    member_id = fields.Many2one(
        'res.partner', string='Member', required=True,
        domain=[('is_member', '=', True)],
    )
    assigned_date = fields.Date(string='Assigned On', default=fields.Date.context_today)
    notes = fields.Char(string='Notes')

    _sql_constraints = [
        ('pastor_member_uniq', 'unique(pastor_id, member_id)',
         'This member is already assigned to this pastor.'),
    ]
