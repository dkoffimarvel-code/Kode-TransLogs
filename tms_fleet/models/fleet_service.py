from odoo import api, fields, models


class FleetVehicleLogServices(models.Model):
    _name = 'fleet.vehicle.log.services'
    _inherit = ['fleet.vehicle.log.services', 'tms.cost.mixin']

    garage = fields.Char('Atelier')
    parts_replaced = fields.Text('Pièces remplacées')
    warranty_covered = fields.Boolean('Sous garantie / contrat d\'entretien')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('cost_center_id') and vals.get('vehicle_id'):
                vals['cost_center_id'] = self.env['fleet.vehicle'].browse(vals['vehicle_id']).cost_center_id.id
        return super().create(vals_list)

    def _tms_cost_category(self):
        return 'maintenance'

    def _tms_cost_amount(self):
        return 0.0 if self.warranty_covered else self.amount

    def _tms_cost_active(self):
        return self.state != 'cancelled'

    def _tms_cost_date(self):
        return self.date or fields.Date.context_today(self)

    def _tms_cost_label(self):
        return 'Maintenance %s' % self.vehicle_id.display_name

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals:
            for rec in self:
                veh = rec.vehicle_id
                if rec.state in ('new', 'running'):
                    veh.tms_status = 'maintenance'
                elif not veh.log_services.filtered(lambda s: s.state in ('new', 'running')) and veh.tms_status == 'maintenance':
                    veh.tms_status = 'available'
        return res
