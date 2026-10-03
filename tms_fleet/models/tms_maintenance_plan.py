from datetime import timedelta

from odoo import api, fields, models


class TmsMaintenancePlan(models.Model):
    _name = 'tms.maintenance.plan'
    _description = 'Plan de maintenance préventive'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Intervention', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', required=True, ondelete='cascade')
    interval_km = fields.Float('Intervalle (km)')
    interval_days = fields.Integer('Intervalle (jours)')
    alert_km = fields.Float('Alerte (km avant échéance)', default=1000)
    alert_days = fields.Integer('Alerte (jours avant échéance)', default=15)
    last_date = fields.Date('Dernière intervention')
    last_odometer = fields.Float('Km dernière intervention')
    next_date = fields.Date('Prochaine échéance (date)', compute='_compute_next', store=True)
    next_odometer = fields.Float('Prochaine échéance (km)', compute='_compute_next', store=True)
    state = fields.Selection([('ok', 'OK'), ('soon', 'Bientôt'), ('overdue', 'En retard')],
                             compute='_compute_state')

    @api.depends('interval_km', 'interval_days', 'last_date', 'last_odometer')
    def _compute_next(self):
        for rec in self:
            rec.next_date = rec.last_date + timedelta(days=rec.interval_days) if rec.last_date and rec.interval_days else False
            rec.next_odometer = rec.last_odometer + rec.interval_km if rec.interval_km else 0.0

    @api.depends('next_date', 'next_odometer', 'vehicle_id.odometer', 'alert_km', 'alert_days')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rec in self:
            km_left = rec.next_odometer - rec.vehicle_id.odometer if rec.next_odometer else None
            days_left = (rec.next_date - today).days if rec.next_date else None
            if (km_left is not None and km_left <= 0) or (days_left is not None and days_left < 0):
                rec.state = 'overdue'
            elif (km_left is not None and km_left <= rec.alert_km) or (days_left is not None and days_left <= rec.alert_days):
                rec.state = 'soon'
            else:
                rec.state = 'ok'

    def action_done(self):
        """Enregistre l'intervention réalisée : repart du kilométrage / date du jour."""
        for rec in self:
            rec.write({'last_date': fields.Date.context_today(rec), 'last_odometer': rec.vehicle_id.odometer})

    @api.model
    def _cron_alerts(self):
        for plan in self.search([]):
            plan._compute_state()
            if plan.state != 'ok' and not plan.activity_ids:
                plan.activity_schedule(
                    'mail.mail_activity_data_todo', date_deadline=plan.next_date or fields.Date.context_today(plan),
                    summary='Maintenance %s : %s' % (plan.state == 'overdue' and 'en retard' or 'à planifier', plan.name),
                    user_id=plan.vehicle_id.manager_id.id or self.env.ref('base.user_admin').id)
