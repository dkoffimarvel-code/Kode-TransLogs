from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    asset_id = fields.Many2one('tms.asset', "Fiche d'immobilisation", copy=False, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        vehicles = super().create(vals_list)
        category = self.env.ref('tms_asset.asset_category_vehicle', raise_if_not_found=False)
        for veh in vehicles:
            if category and not veh.asset_id:
                veh.asset_id = self.env['tms.asset'].create({
                    'name': 'Véhicule %s' % veh.display_name,
                    'category_id': category.id,
                    'vehicle_id': veh.id,
                    'acquisition_date': veh.acquisition_date or fields.Date.context_today(veh),
                    'acquisition_value': veh.car_value or 0.0,
                    'duration_months': category.duration_months,
                    'method': category.method,
                    'cost_center_id': veh.cost_center_id.id,
                })
        return vehicles

    def action_open_asset(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'tms.asset', 'res_id': self.asset_id.id, 'view_mode': 'form'}
