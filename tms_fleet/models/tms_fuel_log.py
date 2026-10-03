from odoo import api, fields, models


class TmsFuelLog(models.Model):
    _name = 'tms.fuel.log'
    _description = 'Plein de carburant'
    _inherit = ['mail.thread', 'tms.cost.mixin']
    _order = 'date desc, odometer desc'

    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule', required=True)
    driver_id = fields.Many2one('hr.employee', 'Conducteur', domain="[('is_driver', '=', True)]")
    date = fields.Date('Date', required=True, default=fields.Date.context_today)
    odometer = fields.Float('Kilométrage')
    liters = fields.Float('Quantité (L)', required=True)
    total_cost = fields.Monetary('Coût total', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    station = fields.Char('Station-service')
    payment_mode = fields.Selection([('card', 'Carte carburant'), ('cash', 'Espèces'), ('transfer', 'Virement')],
                                    'Mode de paiement', default='card')
    receipt = fields.Binary('Justificatif', attachment=True)
    consumption = fields.Float('Conso. (L/100 km)', compute='_compute_consumption', store=True)
    anomaly = fields.Boolean('Anomalie de consommation', compute='_compute_consumption', store=True)

    @api.depends('vehicle_id', 'odometer', 'liters', 'date')
    def _compute_consumption(self):
        for rec in self:
            prev = self.search([('vehicle_id', '=', rec.vehicle_id.id), ('odometer', '<', rec.odometer),
                                ('id', '!=', rec._origin.id)], order='odometer desc', limit=1) if rec.vehicle_id else False
            km = rec.odometer - prev.odometer if prev else 0
            rec.consumption = rec.liters / km * 100 if km > 0 else 0.0
            avg = rec.vehicle_id.fuel_avg_consumption
            # Suspicion de sur-consommation / vol : plus de 30 % au-dessus de la moyenne du véhicule
            rec.anomaly = bool(avg and rec.consumption > 1.3 * avg)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('cost_center_id') and vals.get('vehicle_id'):
                vals['cost_center_id'] = self.env['fleet.vehicle'].browse(vals['vehicle_id']).cost_center_id.id
            if not vals.get('driver_id') and vals.get('vehicle_id'):
                vals['driver_id'] = self.env['fleet.vehicle'].browse(vals['vehicle_id']).tms_driver_id.id
        return super().create(vals_list)

    def _tms_cost_category(self):
        return 'fuel'

    def _tms_cost_amount(self):
        return self.total_cost

    def _tms_cost_date(self):
        return self.date

    def _tms_cost_label(self):
        return 'Carburant %s' % self.vehicle_id.display_name
