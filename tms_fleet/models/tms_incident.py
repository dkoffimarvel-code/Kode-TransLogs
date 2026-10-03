from odoo import api, fields, models


class TmsIncident(models.Model):
    _name = 'tms.incident'
    _description = 'Incident / accident'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tms.cost.mixin']
    _order = 'date desc'

    name = fields.Char('Référence', default='Nouveau', copy=False, readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule concerné', required=True)
    driver_id = fields.Many2one('hr.employee', 'Conducteur', domain="[('is_driver', '=', True)]")
    date = fields.Datetime('Date et heure', required=True, default=fields.Datetime.now)
    incident_type = fields.Selection([('accident', 'Accident'), ('risk', 'Comportement à risque'),
                                      ('breakdown', 'Panne'), ('offence', 'Infraction'), ('other', 'Autre')],
                                     "Type d'incident", required=True, default='accident')
    severity = fields.Selection([('0', 'Mineure'), ('1', 'Moyenne'), ('2', 'Grave')], 'Gravité', default='0')
    description = fields.Text('Description', required=True)
    attachment = fields.Binary('Photo / pièce jointe', attachment=True)
    repair_cost = fields.Monetary('Frais de réparation', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    state = fields.Selection([('open', 'Déclaré'), ('treated', 'Traité')], default='open', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('tms.incident') or 'Nouveau'
            if not vals.get('cost_center_id') and vals.get('vehicle_id'):
                vals['cost_center_id'] = self.env['fleet.vehicle'].browse(vals['vehicle_id']).cost_center_id.id
            if not vals.get('driver_id') and vals.get('vehicle_id'):
                vals['driver_id'] = self.env['fleet.vehicle'].browse(vals['vehicle_id']).tms_driver_id.id
        return super().create(vals_list)

    def _tms_cost_category(self):
        return 'incident'

    def _tms_cost_amount(self):
        return self.repair_cost

    def _tms_cost_date(self):
        return self.date.date()

    def _tms_cost_label(self):
        return 'Incident %s - %s' % (self.name, self.vehicle_id.display_name)

    def action_treat(self):
        self.write({'state': 'treated'})
