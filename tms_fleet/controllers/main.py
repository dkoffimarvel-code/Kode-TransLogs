import hmac

from odoo import fields, http
from odoo.http import request


class TmsGpsController(http.Controller):
    """Réception des positions envoyées par les boîtiers télématiques.

    POST JSON /tms/gps/push  {"token": "...", "device": "REF", "lat": .., "lon": .., "speed": ..}
    Le jeton est le paramètre système ``tms_fleet.gps_token``.
    """

    @http.route('/tms/gps/push', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def gps_push(self, token=None, device=None, lat=None, lon=None, speed=0.0, **kw):
        expected = request.env['ir.config_parameter'].sudo().get_param('tms_fleet.gps_token')
        if not expected or not token or not hmac.compare_digest(str(token), expected):
            return {'status': 'forbidden'}
        vehicle = request.env['fleet.vehicle'].sudo().search([('gps_device_ref', '=', device)], limit=1)
        if not vehicle or lat is None or lon is None:
            return {'status': 'unknown_device'}
        request.env['tms.gps.position'].sudo().create({
            'vehicle_id': vehicle.id, 'latitude': lat, 'longitude': lon, 'speed': speed,
            'date': fields.Datetime.now(),
        })
        return {'status': 'ok'}
