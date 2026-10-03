from odoo import fields, models


class TmsSite(models.Model):
    _name = 'tms.site'
    _description = 'Site / dépôt'

    name = fields.Char('Site / dépôt', required=True)
    address = fields.Char('Adresse')
    cost_center_id = fields.Many2one('account.analytic.account', string='Centre de coût par défaut')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    vehicle_count = fields.Integer(compute='_compute_vehicle_count')

    def _compute_vehicle_count(self):
        data = self.env['fleet.vehicle']._read_group([('tms_site_id', 'in', self.ids)], ['tms_site_id'], ['__count'])
        counts = {s.id: c for s, c in data}
        for rec in self:
            rec.vehicle_count = counts.get(rec.id, 0)
