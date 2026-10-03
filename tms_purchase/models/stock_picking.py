from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    cost_center_id = fields.Many2one('account.analytic.account', 'Centre de coût',
                                     domain="[('plan_id.name', '=', 'Centres de coût')]")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule')
    maintenance_log_id = fields.Many2one('fleet.vehicle.log.services', 'Intervention de maintenance')
    tms_move_kind = fields.Selection([('workshop', 'Consommation atelier'), ('transfer', 'Transfert'),
                                      ('loss', 'Perte / casse')], 'Type de sortie')
    received_by_id = fields.Many2one('res.users', 'Réceptionné par')


class StockMove(models.Model):
    _inherit = 'stock.move'

    reception_state = fields.Selection([('ok', 'Conforme'), ('nok', 'Non conforme'), ('missing', 'Manquant')],
                                       'État à réception')
