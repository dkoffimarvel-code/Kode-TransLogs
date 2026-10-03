from datetime import timedelta

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_driver = fields.Boolean('Conducteur')
    license_number = fields.Char('N° de permis')
    license_categories = fields.Char('Catégories de permis')
    tms_vehicle_ids = fields.One2many('fleet.vehicle', 'tms_driver_id', string='Véhicules assignés')
    tms_site_id = fields.Many2one('tms.site', string='Site de rattachement')
    tms_cost_center_id = fields.Many2one('account.analytic.account', string='Centre de coût',
                                         domain="[('plan_id.name', '=', 'Centres de coût')]")
    tms_document_ids = fields.One2many('tms.document', 'employee_id', string='Habilitations / documents')
    tour_ids = fields.One2many('tms.tour', 'driver_id', string='Tournées')
    incident_ids = fields.One2many('tms.incident', 'driver_id', string='Incidents')
    driving_event_ids = fields.One2many('tms.driving.event', 'driver_id', string='Évènements de conduite')

    tour_month_count = fields.Integer('Missions du mois', compute='_compute_tms_driver_stats')
    incident_count = fields.Integer('Incidents', compute='_compute_tms_driver_stats')
    hard_braking_count = fields.Integer('Freinages brusques (30 j)', compute='_compute_tms_driver_stats')
    safety_score = fields.Float('Score de sécurité', compute='_compute_tms_driver_stats')
    eco_score = fields.Float("Score d'éco-conduite", compute='_compute_tms_driver_stats')
    punctuality_rate = fields.Float('Taux de ponctualité (%)', compute='_compute_tms_driver_stats')
    doc_alert_count = fields.Integer('Documents à renouveler', compute='_compute_tms_driver_stats')

    @api.depends('tour_ids.state', 'tour_ids.date', 'tour_ids.on_time', 'incident_ids',
                 'driving_event_ids.event_type', 'driving_event_ids.date', 'tms_document_ids.state')
    def _compute_tms_driver_stats(self):
        today = fields.Date.context_today(self)
        start_month = today.replace(day=1)
        since = fields.Datetime.now() - timedelta(days=30)
        weights = {'hard_braking': 3, 'harsh_accel': 2, 'speeding': 4, 'idling': 1}
        for rec in self:
            rec.tour_month_count = len(rec.tour_ids.filtered(lambda t: t.date and t.date >= start_month and t.state != 'cancelled'))
            rec.incident_count = len(rec.incident_ids)
            events = rec.driving_event_ids.filtered(lambda e: e.date >= since)
            rec.hard_braking_count = len(events.filtered(lambda e: e.event_type == 'hard_braking'))
            penalty = sum(weights.get(e.event_type, 1) for e in events)
            rec.safety_score = max(0.0, 100.0 - penalty - 5 * len(rec.incident_ids.filtered(lambda i: i.date and i.date >= since)))
            rec.eco_score = max(0.0, 100.0 - 2 * len(events.filtered(lambda e: e.event_type in ('harsh_accel', 'idling', 'hard_braking'))))
            done = rec.tour_ids.filtered(lambda t: t.state == 'done')
            rec.punctuality_rate = (100.0 * len(done.filtered('on_time')) / len(done)) if done else 100.0
            rec.doc_alert_count = len(rec.tms_document_ids.filtered(lambda d: d.state in ('expiring', 'expired')))
