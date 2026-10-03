from datetime import timedelta

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    tms_contract_type = fields.Selection([('cdi', 'CDI'), ('cdd', 'CDD'), ('interim', 'Intérim')], 'Type de contrat')
    tms_contract_end = fields.Date('Fin de contrat')
    tms_contract_due_soon = fields.Boolean(compute='_compute_contract_due_soon', search='_search_contract_due_soon')
    tms_base_salary = fields.Float('Salaire de base mensuel', groups='hr.group_hr_user')
    tms_job_category = fields.Selection([('driver', 'Conducteur'), ('forklift', 'Cariste'), ('workshop', 'Atelier'),
                                         ('operations', 'Exploitation'), ('admin', 'Administratif')], 'Catégorie de personnel')
    tms_payslip_ids = fields.One2many('tms.payslip', 'employee_id', groups='hr.group_hr_user')

    @api.depends('tms_contract_end')
    def _compute_contract_due_soon(self):
        limit = fields.Date.context_today(self) + timedelta(days=30)
        for rec in self:
            rec.tms_contract_due_soon = bool(rec.tms_contract_end and rec.tms_contract_end <= limit)

    def _search_contract_due_soon(self, operator, value):
        limit = fields.Date.context_today(self) + timedelta(days=30)
        if (operator == '=') == bool(value):
            return [('tms_contract_end', '!=', False), ('tms_contract_end', '<=', limit)]
        return ['|', ('tms_contract_end', '=', False), ('tms_contract_end', '>', limit)]

    @api.model
    def _cron_contract_alerts(self):
        for emp in self.search([('tms_contract_due_soon', '=', True)]):
            if not emp.activity_ids:
                emp.activity_schedule('mail.mail_activity_data_todo', date_deadline=emp.tms_contract_end,
                                      summary='Contrat à échéance : %s' % emp.name,
                                      user_id=emp.parent_id.user_id.id or self.env.ref('base.user_admin').id)
