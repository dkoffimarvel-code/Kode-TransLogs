from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class TmsEquipmentIntervention(models.Model):
    _name = 'tms.equipment.intervention'
    _description = 'Intervention sur engin'
    _inherit = ['mail.thread', 'tms.cost.mixin']
    _order = 'date desc'

    equipment_id = fields.Many2one('maintenance.equipment', 'Engin', required=True)
    date = fields.Date('Date', required=True, default=fields.Date.context_today)
    intervention_type = fields.Selection([('preventive', 'Entretien préventif'), ('repair', 'Réparation'),
                                          ('control', 'Contrôle réglementaire')], "Type d'intervention", required=True,
                                         default='preventive')
    provider_id = fields.Many2one('res.partner', 'Prestataire / atelier')
    cost = fields.Monetary('Coût', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    description = fields.Text('Description')
    state = fields.Selection([('draft', 'Brouillon'), ('done', 'Réalisée')], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('cost_center_id') and vals.get('equipment_id'):
                vals['cost_center_id'] = self.env['maintenance.equipment'].browse(vals['equipment_id']).cost_center_id.id
        return super().create(vals_list)

    def action_done(self):
        self.write({'state': 'done'})
        for rec in self.filtered(lambda r: r.intervention_type == 'control'):
            eq = rec.equipment_id
            eq.next_control_date = rec.date + relativedelta(months=eq.control_interval_months or 12)
        self._sync_analytic_line()

    def _tms_cost_category(self):
        return 'maintenance'

    def _tms_cost_amount(self):
        return self.cost

    def _tms_cost_active(self):
        return self.state == 'done'

    def _tms_cost_date(self):
        return self.date

    def _tms_cost_label(self):
        return 'Intervention engin %s' % self.equipment_id.name
