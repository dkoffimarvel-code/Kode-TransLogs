from datetime import timedelta

from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    tms_site_id = fields.Many2one('tms.site', "Site d'affectation")
    cost_center_id = fields.Many2one('account.analytic.account', 'Centre de coût',
                                     domain="[('plan_id.name', '=', 'Centres de coût')]")
    commissioning_date = fields.Date('Date de mise en service')
    tms_state = fields.Selection([('operational', 'Opérationnel'), ('maintenance', 'En maintenance'),
                                  ('out', 'Hors service')], 'Statut opérationnel', default='operational')
    next_control_date = fields.Date('Prochain contrôle réglementaire')
    control_interval_months = fields.Integer('Périodicité du contrôle (mois)', default=12)
    control_due_soon = fields.Boolean(compute='_compute_control_due_soon', search='_search_control_due_soon')
    intervention_ids = fields.One2many('tms.equipment.intervention', 'equipment_id', 'Interventions')
    maintenance_cost_total = fields.Float('Coût de maintenance', compute='_compute_cost')
    last_intervention_date = fields.Date('Dernière intervention', compute='_compute_cost')

    @api.depends('intervention_ids.cost', 'intervention_ids.date')
    def _compute_cost(self):
        for rec in self:
            rec.maintenance_cost_total = sum(rec.intervention_ids.mapped('cost'))
            rec.last_intervention_date = max(rec.intervention_ids.mapped('date') or [False])

    @api.depends('next_control_date')
    def _compute_control_due_soon(self):
        limit = fields.Date.context_today(self) + timedelta(days=30)
        for rec in self:
            rec.control_due_soon = bool(rec.next_control_date and rec.next_control_date <= limit)

    def _search_control_due_soon(self, operator, value):
        limit = fields.Date.context_today(self) + timedelta(days=30)
        positive = (operator == '=') == bool(value)
        return [('next_control_date', '<=' if positive else '>', limit)] if positive else \
            ['|', ('next_control_date', '=', False), ('next_control_date', '>', limit)]

    @api.model
    def _cron_regulatory_controls(self):
        for eq in self.search([('control_due_soon', '=', True)]):
            if not eq.activity_ids:
                eq.activity_schedule('mail.mail_activity_data_todo', date_deadline=eq.next_control_date,
                                     summary='Contrôle réglementaire à planifier : %s' % eq.name,
                                     user_id=eq.technician_user_id.id or self.env.ref('base.user_admin').id)
