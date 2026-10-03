from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    tms_cost_center_id = fields.Many2one('account.analytic.account', 'Centre de coût',
                                         domain="[('plan_id.name', '=', 'Centres de coût')]")
    tms_reimbursement = fields.Selection([('payroll', 'Via la paie'), ('transfer', 'Virement séparé')],
                                         'Mode de remboursement', default='payroll')

    def _apply_cost_center(self):
        for exp in self.filtered('tms_cost_center_id'):
            exp.analytic_distribution = {str(exp.tms_cost_center_id.id): 100}

    @api.onchange('employee_id')
    def _onchange_employee_cost_center(self):
        if self.employee_id.tms_cost_center_id and not self.tms_cost_center_id:
            self.tms_cost_center_id = self.employee_id.tms_cost_center_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('tms_cost_center_id') and vals.get('employee_id'):
                vals['tms_cost_center_id'] = self.env['hr.employee'].browse(vals['employee_id']).tms_cost_center_id.id
        recs = super().create(vals_list)
        recs._apply_cost_center()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if 'tms_cost_center_id' in vals:
            self._apply_cost_center()
        return res
