from datetime import timedelta

from odoo import api, fields, models

TMS_STATUS = [
    ('available', 'Disponible'),
    ('in_service', 'En circulation'),
    ('maintenance', 'En maintenance'),
    ('out_of_service', 'Hors service'),
]


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    tms_status = fields.Selection(TMS_STATUS, string='Statut opérationnel', default='available',
                                  tracking=True, group_expand='_group_expand_tms_status')
    tms_site_id = fields.Many2one('tms.site', string='Site / dépôt', tracking=True)
    cost_center_id = fields.Many2one(
        'account.analytic.account', string='Centre de coût', tracking=True,
        domain="[('plan_id.name', '=', 'Centres de coût')]",
        help="Rattachement budgétaire par défaut du véhicule.")
    load_capacity = fields.Float('Capacité de charge (kg)')
    fuel_type_tms = fields.Selection(related='fuel_type', string='Carburant', readonly=False)
    commissioning_date = fields.Date('Date de mise en service')
    gps_device_ref = fields.Char('N° boîtier GPS')
    gps_active = fields.Boolean('Suivi GPS actif', compute='_compute_gps_active', store=True)
    last_latitude = fields.Float('Dernière latitude', digits=(10, 6), readonly=True)
    last_longitude = fields.Float('Dernière longitude', digits=(10, 6), readonly=True)
    last_position_date = fields.Datetime('Dernière position', readonly=True)
    last_speed = fields.Float('Dernière vitesse (km/h)', readonly=True)
    tms_driver_id = fields.Many2one('hr.employee', string='Conducteur assigné',
                                    domain="[('is_driver', '=', True)]", tracking=True)

    tms_document_ids = fields.One2many('tms.document', 'vehicle_id', string='Documents')
    tour_ids = fields.One2many('tms.tour', 'vehicle_id', string='Tournées')
    fuel_log_ids = fields.One2many('tms.fuel.log', 'vehicle_id', string='Pleins')
    incident_ids = fields.One2many('tms.incident', 'vehicle_id', string='Incidents')
    position_ids = fields.One2many('tms.gps.position', 'vehicle_id', string='Positions')
    maintenance_plan_ids = fields.One2many('tms.maintenance.plan', 'vehicle_id', string='Plans de maintenance')

    open_repairs_count = fields.Integer('Réparations en cours', compute='_compute_tms_stats')
    fuel_avg_consumption = fields.Float('Conso. moyenne (L/100 km)', compute='_compute_tms_stats')
    fuel_cost_total = fields.Float('Coût carburant', compute='_compute_tms_stats')
    maintenance_cost_total = fields.Float('Coût maintenance', compute='_compute_tms_stats')
    total_cost = fields.Float("Coût d'exploitation total", compute='_compute_tms_stats')
    cost_per_km = fields.Float('Coût au km', compute='_compute_tms_stats')
    doc_expired_count = fields.Integer('Documents expirés / à renouveler', compute='_compute_tms_stats')

    @api.model
    def _group_expand_tms_status(self, states, domain):
        return [key for key, _label in TMS_STATUS]

    @api.depends('gps_device_ref')
    def _compute_gps_active(self):
        for rec in self:
            rec.gps_active = bool(rec.gps_device_ref)

    @api.depends('fuel_log_ids.liters', 'fuel_log_ids.total_cost', 'fuel_log_ids.odometer',
                 'log_services.amount', 'log_services.state', 'odometer', 'tms_document_ids.state',
                 'incident_ids.repair_cost')
    def _compute_tms_stats(self):
        for rec in self:
            fuels = rec.fuel_log_ids.sorted('odometer')
            rec.fuel_cost_total = sum(fuels.mapped('total_cost'))
            kms = (fuels[-1].odometer - fuels[0].odometer) if len(fuels) > 1 else 0
            liters = sum(fuels[1:].mapped('liters')) if len(fuels) > 1 else 0
            rec.fuel_avg_consumption = (liters / kms * 100) if kms > 0 else 0.0
            services = rec.log_services.filtered(lambda s: s.state != 'cancelled')
            rec.maintenance_cost_total = sum(services.mapped('amount'))
            rec.open_repairs_count = len(services.filtered(lambda s: s.state in ('new', 'running')))
            rec.total_cost = rec.fuel_cost_total + rec.maintenance_cost_total + sum(rec.incident_ids.mapped('repair_cost'))
            rec.cost_per_km = rec.total_cost / rec.odometer if rec.odometer else 0.0
            rec.doc_expired_count = len(rec.tms_document_ids.filtered(lambda d: d.state in ('expiring', 'expired')))

    def action_open_map(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url', 'target': 'new',
            'url': 'https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=15/%s/%s' % (
                self.last_latitude, self.last_longitude, self.last_latitude, self.last_longitude),
        }

    def action_view_tms(self):
        self.ensure_one()
        model = self.env.context.get('tms_model')
        return {
            'type': 'ir.actions.act_window', 'res_model': model, 'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)], 'context': {'default_vehicle_id': self.id},
            'name': self.display_name,
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('tms_site_id') and not vals.get('cost_center_id'):
                site = self.env['tms.site'].browse(vals['tms_site_id'])
                vals['cost_center_id'] = site.cost_center_id.id
        return super().create(vals_list)

    @api.onchange('tms_site_id')
    def _onchange_tms_site_id(self):
        if self.tms_site_id.cost_center_id and not self.cost_center_id:
            self.cost_center_id = self.tms_site_id.cost_center_id
