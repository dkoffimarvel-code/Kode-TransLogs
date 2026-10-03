from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    tms_request_id = fields.Many2one('tms.purchase.request', "Demande d'achat", copy=False)
    cost_center_id = fields.Many2one('account.analytic.account', 'Centre de coût',
                                     domain="[('plan_id.name', '=', 'Centres de coût')]")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule concerné')

    def _apply_cost_center(self):
        for order in self.filtered('cost_center_id'):
            order.order_line.filtered(lambda l: not l.analytic_distribution and not l.display_type).write({
                'analytic_distribution': {str(order.cost_center_id.id): 100}})

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._apply_cost_center()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if 'cost_center_id' in vals or 'order_line' in vals:
            self._apply_cost_center()
        return res
