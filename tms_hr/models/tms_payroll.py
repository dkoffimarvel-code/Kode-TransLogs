from odoo import api, fields, models
from odoo.exceptions import UserError


class TmsPayElement(models.Model):
    _name = 'tms.pay.element'
    _description = 'Élément variable de paie'
    _inherit = ['tms.cost.mixin']
    _order = 'period desc'

    employee_id = fields.Many2one('hr.employee', 'Employé', required=True)
    period = fields.Date('Période (1er du mois)', required=True,
                         default=lambda s: fields.Date.context_today(s).replace(day=1))
    element_type = fields.Selection([('bonus', 'Prime'), ('overtime', 'Heures supplémentaires'),
                                     ('mileage', 'Indemnité kilométrique'), ('risk', 'Prime de risque'),
                                     ('deduction', 'Retenue')], 'Type', required=True, default='bonus')
    amount = fields.Monetary('Montant', required=True, currency_field='currency_id')
    recurring = fields.Boolean('Récurrent')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('cost_center_id') and vals.get('employee_id'):
                vals['cost_center_id'] = self.env['hr.employee'].browse(vals['employee_id']).tms_cost_center_id.id
        return super().create(vals_list)

    def _signed_amount(self):
        self.ensure_one()
        return -self.amount if self.element_type == 'deduction' else self.amount


class TmsPayslip(models.Model):
    _name = 'tms.payslip'
    _description = 'Bulletin de paie'
    _inherit = ['mail.thread', 'tms.cost.mixin']
    _order = 'period desc, employee_id'

    employee_id = fields.Many2one('hr.employee', 'Employé', required=True)
    period = fields.Date('Période', required=True, default=lambda s: fields.Date.context_today(s).replace(day=1))
    base_salary = fields.Monetary('Salaire de base', currency_field='currency_id')
    variable_amount = fields.Monetary('Éléments variables', currency_field='currency_id')
    expense_amount = fields.Monetary('Notes de frais remboursées', currency_field='currency_id')
    gross = fields.Monetary('Salaire brut', compute='_compute_amounts', store=True, currency_field='currency_id')
    social_charges = fields.Monetary('Charges sociales', compute='_compute_amounts', store=True, currency_field='currency_id')
    net = fields.Monetary('Salaire net', compute='_compute_amounts', store=True, currency_field='currency_id')
    employer_cost = fields.Monetary('Coût employeur', compute='_compute_amounts', store=True, currency_field='currency_id')
    state = fields.Selection([('draft', 'Brouillon'), ('validated', 'Validé'), ('paid', 'Payé')], default='draft', tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    @api.depends('base_salary', 'variable_amount', 'expense_amount')
    def _compute_amounts(self):
        icp = self.env['ir.config_parameter'].sudo()
        employee_rate = float(icp.get_param('tms_hr.employee_charge_rate', 22.0)) / 100
        employer_rate = float(icp.get_param('tms_hr.employer_charge_rate', 42.0)) / 100
        for rec in self:
            rec.gross = rec.base_salary + rec.variable_amount
            rec.social_charges = rec.gross * employee_rate
            rec.net = rec.gross - rec.social_charges + rec.expense_amount
            rec.employer_cost = rec.gross * (1 + employer_rate)

    @api.model
    def _prepare_from_employee(self, employee, period):
        elements = self.env['tms.pay.element'].search([('employee_id', '=', employee.id), ('period', '=', period)])
        expenses = self.env['hr.expense'].search([
            ('employee_id', '=', employee.id), ('tms_reimbursement', '=', 'payroll'),
            ('state', 'in', ('approved', 'done')), ('date', '>=', period),
            ('date', '<', fields.Date.add(period, months=1))])
        return {
            'employee_id': employee.id, 'period': period,
            'base_salary': employee.sudo().tms_base_salary,
            'variable_amount': sum(e._signed_amount() for e in elements),
            'expense_amount': sum(expenses.mapped('total_amount')),
            'cost_center_id': employee.tms_cost_center_id.id,
        }

    @api.model
    def action_generate_month(self, period=None):
        """Génère les bulletins brouillon du mois pour tout le personnel sous contrat."""
        period = period or fields.Date.context_today(self).replace(day=1)
        created = self.browse()
        for emp in self.env['hr.employee'].sudo().search([('tms_base_salary', '>', 0)]):
            if self.search_count([('employee_id', '=', emp.id), ('period', '=', period)]):
                continue
            created |= self.create(self._prepare_from_employee(emp, period))
        return created

    def action_refresh(self):
        for rec in self.filtered(lambda r: r.state == 'draft'):
            rec.write(self._prepare_from_employee(rec.employee_id, rec.period))

    def action_validate(self):
        self.write({'state': 'validated'})
        self._sync_analytic_line()

    def action_paid(self):
        if any(s.state != 'validated' for s in self):
            raise UserError("Seuls les bulletins validés peuvent être marqués payés.")
        self.write({'state': 'paid'})

    def _tms_cost_category(self):
        return 'salary'

    def _tms_cost_amount(self):
        return self.employer_cost

    def _tms_cost_active(self):
        return self.state in ('validated', 'paid')

    def _tms_cost_date(self):
        return self.period

    def _tms_cost_label(self):
        return 'Paie %s %s' % (self.employee_id.name, self.period)
