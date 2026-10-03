from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class TmsTour(models.Model):
    _name = 'tms.tour'
    _description = 'Tournée'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tms.cost.mixin']
    _order = 'date desc, departure_time'

    name = fields.Char('Référence', default='Nouveau', copy=False, readonly=True)
    driver_id = fields.Many2one('hr.employee', 'Conducteur', required=True, tracking=True,
                                domain="[('is_driver', '=', True)]")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule', required=True, tracking=True)
    date = fields.Date('Date', required=True, default=fields.Date.context_today, tracking=True)
    departure_time = fields.Float('Heure de départ')
    zone = fields.Char('Zone / trajet', required=True)
    priority = fields.Selection([('normal', 'Normale'), ('urgent', 'Urgente')], default='normal', tracking=True)
    state = fields.Selection([('draft', 'Brouillon'), ('planned', 'Planifiée'), ('in_progress', 'En cours'),
                              ('done', 'Terminée'), ('cancelled', 'Annulée')],
                             default='draft', tracking=True, group_expand='_group_expand_state')
    stop_ids = fields.One2many('tms.tour.stop', 'tour_id', 'Points de livraison')
    stop_count = fields.Integer(compute='_compute_stop_count')
    distance_km = fields.Float('Distance (km)')
    empty_km = fields.Float('Km à vide')
    on_time = fields.Boolean('Livrée à l\'heure', default=True)
    customer_id = fields.Many2one('res.partner', 'Client')
    billing_mode = fields.Selection([('flat', 'Au forfait'), ('km', 'Au kilomètre'), ('tour', 'À la tournée')],
                                    'Mode de facturation', default='flat')
    unit_price = fields.Monetary('Prix unitaire', currency_field='currency_id')
    amount_to_invoice = fields.Monetary('Montant à facturer', compute='_compute_amount', store=True,
                                        currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    invoice_id = fields.Many2one('account.move', 'Facture client', copy=False, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model
    def _group_expand_state(self, states, domain):
        return ['draft', 'planned', 'in_progress', 'done']

    @api.depends('stop_ids')
    def _compute_stop_count(self):
        for rec in self:
            rec.stop_count = len(rec.stop_ids)

    @api.depends('billing_mode', 'unit_price', 'distance_km')
    def _compute_amount(self):
        for rec in self:
            rec.amount_to_invoice = rec.unit_price * rec.distance_km if rec.billing_mode == 'km' else rec.unit_price

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.driver_id = self.driver_id or self.vehicle_id.tms_driver_id
            self.cost_center_id = self.vehicle_id.cost_center_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('tms.tour') or 'Nouveau'
            if not vals.get('cost_center_id') and vals.get('vehicle_id'):
                vals['cost_center_id'] = self.env['fleet.vehicle'].browse(vals['vehicle_id']).cost_center_id.id
        return super().create(vals_list)

    @api.constrains('driver_id', 'vehicle_id', 'date', 'state')
    def _check_availability(self):
        """Contrainte d'affectation : un conducteur / véhicule ne peut avoir deux tournées le même jour."""
        for rec in self.filtered(lambda t: t.state != 'cancelled'):
            for field, label in (('driver_id', 'conducteur'), ('vehicle_id', 'véhicule')):
                clash = self.search_count([
                    ('id', '!=', rec.id), ('date', '=', rec.date), ('state', '!=', 'cancelled'),
                    (field, '=', rec[field].id)])
                if clash:
                    raise ValidationError("Le %s %s est déjà affecté à une autre tournée le %s." % (
                        label, rec[field].display_name, rec.date))

    def action_plan(self):
        for rec in self:
            blocking = rec.vehicle_id.tms_document_ids.filtered(lambda d: d.state == 'expired') | \
                rec.driver_id.tms_document_ids.filtered(lambda d: d.state == 'expired')
            if blocking:
                raise UserError("Documents expirés : %s" % ', '.join(blocking.mapped('name')))
        self.write({'state': 'planned'})

    def action_start(self):
        self.write({'state': 'in_progress'})
        self.mapped('vehicle_id').write({'tms_status': 'in_service'})

    def action_done(self):
        self.write({'state': 'done'})
        for veh in self.mapped('vehicle_id'):
            if not veh.tour_ids.filtered(lambda t: t.state == 'in_progress'):
                veh.tms_status = 'available'

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_create_invoice(self):
        """§7.1 : facture client générée à partir des tournées réalisées."""
        for tour in self:
            if tour.state != 'done' or tour.invoice_id or not tour.customer_id:
                raise UserError("La tournée %s doit être terminée, avoir un client et ne pas être déjà facturée." % tour.name)
        for customer, tours in self.grouped('customer_id').items():
            move = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': customer.id,
                'invoice_date': fields.Date.context_today(self),
                'invoice_line_ids': [(0, 0, {
                    'name': 'Transport %s - %s (%s)' % (t.name, t.zone, t.date),
                    'quantity': 1,
                    'price_unit': t.amount_to_invoice,
                    'analytic_distribution': {str(t.cost_center_id.id): 100} if t.cost_center_id else False,
                }) for t in tours],
            })
            tours.invoice_id = move
        return True

    def _tms_cost_amount(self):
        return 0.0


class TmsTourStop(models.Model):
    _name = 'tms.tour.stop'
    _description = 'Point de livraison'
    _order = 'sequence, id'

    tour_id = fields.Many2one('tms.tour', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    partner_id = fields.Many2one('res.partner', 'Client / lieu', required=True)
    address = fields.Char('Adresse', related='partner_id.contact_address_complete', readonly=True)
    window_start = fields.Float('Début fenêtre')
    window_end = fields.Float('Fin fenêtre')
    weight = fields.Float('Poids (kg)')
    state = fields.Selection([('todo', 'À livrer'), ('done', 'Livré'), ('failed', 'Échec')], default='todo')
    proof = fields.Binary('Preuve de livraison', attachment=True)

    @api.constrains('weight', 'tour_id')
    def _check_capacity(self):
        for tour in self.mapped('tour_id'):
            cap = tour.vehicle_id.load_capacity
            if cap and sum(tour.stop_ids.mapped('weight')) > cap:
                raise ValidationError("La charge de la tournée %s dépasse la capacité du véhicule (%s kg)." % (tour.name, cap))
