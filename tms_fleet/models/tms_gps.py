import math

from odoo import api, fields, models


class TmsGpsPosition(models.Model):
    _name = 'tms.gps.position'
    _description = 'Position GPS'
    _order = 'date desc'

    vehicle_id = fields.Many2one('fleet.vehicle', required=True, index=True, ondelete='cascade')
    date = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    latitude = fields.Float(digits=(10, 6), required=True)
    longitude = fields.Float(digits=(10, 6), required=True)
    speed = fields.Float('Vitesse (km/h)')

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            veh = rec.vehicle_id
            if not veh.last_position_date or rec.date >= veh.last_position_date:
                veh.sudo().write({'last_latitude': rec.latitude, 'last_longitude': rec.longitude,
                                  'last_position_date': rec.date, 'last_speed': rec.speed})
            self.env['tms.geofence']._check_position(rec)
        return recs

    @api.autovacuum
    def _gc_old_positions(self):
        days = int(self.env['ir.config_parameter'].sudo().get_param('tms_fleet.gps_history_days', 90))
        limit = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        self.search([('date', '<', limit)]).unlink()


class TmsGeofence(models.Model):
    _name = 'tms.geofence'
    _description = 'Zone (géofencing)'

    name = fields.Char(required=True)
    latitude = fields.Float(digits=(10, 6), required=True)
    longitude = fields.Float(digits=(10, 6), required=True)
    radius_km = fields.Float('Rayon (km)', required=True, default=5.0)
    vehicle_ids = fields.Many2many('fleet.vehicle', string='Véhicules surveillés (vide = tous)')
    active = fields.Boolean(default=True)

    @staticmethod
    def _distance_km(lat1, lon1, lat2, lon2):
        p = math.pi / 180
        a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
        return 12742 * math.asin(math.sqrt(a))

    @api.model
    def _check_position(self, position):
        """Alerte de sortie de zone : activité planifiée sur le véhicule."""
        veh = position.vehicle_id
        for zone in self.search([]):
            if zone.vehicle_ids and veh not in zone.vehicle_ids:
                continue
            if self._distance_km(zone.latitude, zone.longitude, position.latitude, position.longitude) > zone.radius_km:
                veh.message_post(body="Alerte géofencing : %s est sorti de la zone « %s »." % (veh.display_name, zone.name),
                                 subtype_xmlid='mail.mt_comment')
