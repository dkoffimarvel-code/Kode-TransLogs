from odoo import api, fields, models
from odoo.exceptions import UserError


class TmsPurchaseRequest(models.Model):
    _name = 'tms.purchase.request'
    _description = "Demande d'achat"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Référence', default='Nouveau', copy=False, readonly=True)
    requester_id = fields.Many2one('res.users', 'Demandeur', required=True, default=lambda s: s.env.user)
    date = fields.Date('Date', required=True, default=fields.Date.context_today)
    site_id = fields.Many2one('tms.site', 'Site / dépôt')
    cost_center_id = fields.Many2one('account.analytic.account', 'Centre de coût', required=True,
                                     domain="[('plan_id.name', '=', 'Centres de coût')]")
    justification = fields.Text('Justification')
    state = fields.Selection([('draft', 'Brouillon'), ('to_approve', 'À valider'), ('approved', 'Validée'),
                              ('ordered', 'Commandée'), ('refused', 'Refusée')], default='draft', tracking=True)
    line_ids = fields.One2many('tms.purchase.request.line', 'request_id', 'Lignes')
    order_ids = fields.One2many('purchase.order', 'tms_request_id', 'Commandes')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('tms.purchase.request') or 'Nouveau'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Ajoutez au moins une ligne.")
            rec.state = 'to_approve'
            rec.activity_schedule('mail.mail_activity_data_todo', summary="Demande d'achat à valider",
                                  user_id=(rec.requester_id.employee_id.parent_id.user_id.id or self.env.ref('base.user_admin').id))

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_refuse(self):
        self.write({'state': 'refused'})

    def action_create_order(self):
        """Transforme la demande validée en commande fournisseur (brouillon) par fournisseur."""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError("La demande doit être validée.")
        supplier = self.line_ids.mapped('product_id.seller_ids.partner_id')[:1] or self.env['res.partner'].search([('supplier_rank', '>', 0)], limit=1)
        if not supplier:
            raise UserError("Aucun fournisseur disponible : renseignez-en un sur l'article.")
        order = self.env['purchase.order'].create({
            'partner_id': supplier.id,
            'tms_request_id': self.id,
            'cost_center_id': self.cost_center_id.id,
            'order_line': [(0, 0, {
                'product_id': l.product_id.id, 'name': l.name or l.product_id.display_name,
                'product_qty': l.quantity, 'product_uom_id': l.product_id.uom_id.id,
            }) for l in self.line_ids],
        })
        self.state = 'ordered'
        return {'type': 'ir.actions.act_window', 'res_model': 'purchase.order', 'res_id': order.id, 'view_mode': 'form'}


class TmsPurchaseRequestLine(models.Model):
    _name = 'tms.purchase.request.line'
    _description = "Ligne de demande d'achat"

    request_id = fields.Many2one('tms.purchase.request', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Article', required=True)
    name = fields.Char('Désignation')
    quantity = fields.Float('Quantité', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.name = self.product_id.display_name
