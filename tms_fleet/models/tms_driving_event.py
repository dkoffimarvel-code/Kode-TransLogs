from odoo import fields, models


class TmsDrivingEvent(models.Model):
    _name = 'tms.driving.event'
    _description = 'Évènement de conduite'
    _order = 'date desc'

    driver_id = fields.Many2one('hr.employee', 'Conducteur', required=True, domain="[('is_driver', '=', True)]")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule', required=True)
    date = fields.Datetime('Date', default=fields.Datetime.now, required=True)
    event_type = fields.Selection([('hard_braking', 'Freinage brusque'), ('harsh_accel', 'Accélération brusque'),
                                   ('speeding', 'Survitesse'), ('idling', 'Ralenti prolongé')], 'Type', required=True)
    value = fields.Float('Valeur mesurée')
