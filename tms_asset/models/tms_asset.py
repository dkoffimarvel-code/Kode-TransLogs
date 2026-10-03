from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class TmsAssetCategory(models.Model):
    _name = 'tms.asset.category'
    _description = "Catégorie d'immobilisation"

    name = fields.Char(required=True)
    code = fields.Selection([('vehicle', 'Véhicules'), ('building', 'Bâtiments'), ('it', 'Matériel informatique'),
                             ('furniture', 'Mobilier'), ('other', 'Autre')], required=True, default='other')
    duration_months = fields.Integer("Durée d'amortissement par défaut (mois)", default=60)
    method = fields.Selection([('linear', 'Linéaire'), ('degressive', 'Dégressif')], default='linear')
    journal_id = fields.Many2one('account.journal', 'Journal des OD', domain="[('type', '=', 'general')]")
    asset_account_id = fields.Many2one('account.account', "Compte d'immobilisation")
    depreciation_account_id = fields.Many2one('account.account', "Compte d'amortissement (bilan)")
    expense_account_id = fields.Many2one('account.account', 'Compte de dotation (charge)')


class TmsAsset(models.Model):
    _name = 'tms.asset'
    _description = 'Immobilisation'
    _inherit = ['mail.thread', 'tms.cost.mixin']
    _order = 'acquisition_date desc'

    name = fields.Char('Désignation', required=True, tracking=True)
    category_id = fields.Many2one('tms.asset.category', 'Catégorie', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Véhicule', copy=False)
    acquisition_date = fields.Date("Date d'acquisition", required=True, default=fields.Date.context_today)
    acquisition_value = fields.Monetary("Valeur d'acquisition", required=True, currency_field='currency_id')
    salvage_value = fields.Monetary('Valeur résiduelle', currency_field='currency_id')
    duration_months = fields.Integer("Durée d'amortissement (mois)", required=True)
    method = fields.Selection([('linear', 'Linéaire'), ('degressive', 'Dégressif')], required=True, default='linear')
    degressive_factor = fields.Float('Coefficient dégressif', default=1.75)
    state = fields.Selection([('draft', 'Brouillon'), ('running', 'En cours'), ('sold', 'Cédée'),
                              ('scrapped', 'Mise au rebut')], default='draft', tracking=True)
    line_ids = fields.One2many('tms.asset.line', 'asset_id', "Plan d'amortissement")
    accumulated = fields.Monetary('Amortissement cumulé', compute='_compute_values', store=True, currency_field='currency_id')
    book_value = fields.Monetary('Valeur nette comptable', compute='_compute_values', store=True, currency_field='currency_id')
    fully_depreciated = fields.Boolean('Totalement amorti', compute='_compute_values', store=True)
    disposal_date = fields.Date('Date de sortie')
    disposal_value = fields.Monetary('Prix de cession', currency_field='currency_id')
    gain_loss = fields.Monetary('Plus / moins-value', compute='_compute_gain_loss', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('line_ids.amount', 'line_ids.state', 'acquisition_value')
    def _compute_values(self):
        for rec in self:
            rec.accumulated = sum(rec.line_ids.filtered(lambda l: l.state == 'posted').mapped('amount'))
            rec.book_value = rec.acquisition_value - rec.accumulated
            rec.fully_depreciated = bool(rec.line_ids) and rec.book_value <= rec.salvage_value

    @api.depends('disposal_value', 'book_value', 'state')
    def _compute_gain_loss(self):
        for rec in self:
            rec.gain_loss = rec.disposal_value - rec.book_value if rec.state in ('sold', 'scrapped') else 0.0

    @api.onchange('category_id')
    def _onchange_category(self):
        if self.category_id:
            self.duration_months = self.category_id.duration_months
            self.method = self.category_id.method

    def _tms_cost_amount(self):
        return 0.0

    def action_compute_plan(self):
        """Plan d'amortissement mensuel (linéaire ou dégressif)."""
        for rec in self:
            if rec.state != 'draft' and rec.line_ids.filtered(lambda l: l.state == 'posted'):
                raise UserError("Des dotations sont déjà comptabilisées.")
            rec.line_ids.unlink()
            base = rec.acquisition_value - rec.salvage_value
            n = max(rec.duration_months, 1)
            remaining = base
            vals = []
            for i in range(n):
                if rec.method == 'linear':
                    amount = base / n
                else:
                    rate = rec.degressive_factor / n
                    remaining_months = n - i
                    amount = max(remaining * rate, remaining / remaining_months) if remaining_months > 1 else remaining
                amount = min(amount, remaining)
                remaining -= amount
                vals.append({'asset_id': rec.id, 'date': rec.acquisition_date + relativedelta(months=i + 1, day=31),
                             'amount': amount, 'cost_center_id': rec.cost_center_id.id})
            self.env['tms.asset.line'].create(vals)

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                rec.action_compute_plan()
        self.write({'state': 'running'})

    def action_sell(self):
        self.write({'state': 'sold', 'disposal_date': fields.Date.context_today(self)})

    def action_scrap(self):
        self.write({'state': 'scrapped', 'disposal_date': fields.Date.context_today(self)})
        self.mapped('vehicle_id').write({'tms_status': 'out_of_service'})

    @api.model
    def _cron_post_depreciation(self):
        lines = self.env['tms.asset.line'].search([
            ('state', '=', 'draft'), ('date', '<=', fields.Date.context_today(self)),
            ('asset_id.state', '=', 'running')])
        lines.action_post()


class TmsAssetLine(models.Model):
    _name = 'tms.asset.line'
    _description = "Dotation aux amortissements"
    _inherit = ['tms.cost.mixin']
    _order = 'date'

    asset_id = fields.Many2one('tms.asset', required=True, ondelete='cascade')
    date = fields.Date('Date', required=True)
    amount = fields.Monetary('Dotation', required=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='asset_id.currency_id')
    state = fields.Selection([('draft', 'Prévue'), ('posted', 'Comptabilisée')], default='draft')
    move_id = fields.Many2one('account.move', 'Écriture', readonly=True)

    def _tms_cost_category(self):
        return 'depreciation'

    def _tms_cost_amount(self):
        return self.amount

    def _tms_cost_active(self):
        return self.state == 'posted'

    def _tms_cost_date(self):
        return self.date

    def _tms_cost_label(self):
        return 'Dotation %s' % self.asset_id.name

    def action_post(self):
        for line in self.filtered(lambda l: l.state == 'draft'):
            cat = line.asset_id.category_id
            if cat.journal_id and cat.expense_account_id and cat.depreciation_account_id:
                move = self.env['account.move'].create({
                    'move_type': 'entry', 'journal_id': cat.journal_id.id, 'date': line.date,
                    'ref': 'Amortissement %s' % line.asset_id.name,
                    'line_ids': [
                        (0, 0, {'account_id': cat.expense_account_id.id, 'debit': line.amount, 'credit': 0.0,
                                'name': line.asset_id.name,
                                'analytic_distribution': {str(line.asset_id.cost_center_id.id): 100} if line.asset_id.cost_center_id else False}),
                        (0, 0, {'account_id': cat.depreciation_account_id.id, 'debit': 0.0, 'credit': line.amount,
                                'name': line.asset_id.name}),
                    ],
                })
                move.action_post()
                line.move_id = move
            line.state = 'posted'
            line.cost_center_id = line.asset_id.cost_center_id
            line._sync_analytic_line()
