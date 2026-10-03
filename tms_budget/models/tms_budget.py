from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.tms_fleet.models.tms_cost_mixin import TMS_CATEGORIES  # noqa: E402


class TmsBudget(models.Model):
    _name = 'tms.budget'
    _description = 'Budget par centre de coût'
    _inherit = ['mail.thread']
    _order = 'fiscal_year desc, cost_center_id'

    name = fields.Char(compute='_compute_name', store=True)
    cost_center_id = fields.Many2one('account.analytic.account', 'Centre de coût', required=True,
                                     domain="[('plan_id.name', '=', 'Centres de coût')]")
    fiscal_year = fields.Integer('Exercice budgétaire', required=True, default=lambda s: fields.Date.context_today(s).year)
    category = fields.Selection(TMS_CATEGORIES, 'Catégorie de dépense',
                                help="Vide = toutes catégories confondues (budget global du centre de coût).")
    period = fields.Selection([('year', 'Annuel'), ('quarter', 'Trimestriel'), ('month', 'Mensuel')], 'Période',
                              default='year', required=True)
    period_number = fields.Integer('N° de période', default=1,
                                   help="Trimestre (1-4) ou mois (1-12). Ignoré pour un budget annuel.")
    amount = fields.Monetary('Montant budgété', required=True, currency_field='currency_id')
    threshold = fields.Float('Seuil d\'alerte (%)', default=90.0)
    date_from = fields.Date(compute='_compute_dates', store=True)
    date_to = fields.Date(compute='_compute_dates', store=True)
    actual = fields.Monetary('Réalisé', compute='_compute_actual', currency_field='currency_id')
    gap = fields.Monetary('Écart', compute='_compute_actual', currency_field='currency_id')
    consumed_pct = fields.Float('% consommé', compute='_compute_actual')
    state = fields.Selection([('ok', 'Dans le budget'), ('warning', 'Seuil approché'), ('over', 'Dépassé')],
                             compute='_compute_actual')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('cost_center_id', 'fiscal_year', 'category', 'period', 'period_number')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s / %s%s' % (rec.cost_center_id.name or '', rec.fiscal_year,
                                      ' / %s' % dict(TMS_CATEGORIES).get(rec.category, '') if rec.category else '')

    @api.constrains('period', 'period_number')
    def _check_period(self):
        for rec in self:
            limit = {'year': 1, 'quarter': 4, 'month': 12}[rec.period]
            if not 1 <= rec.period_number <= limit:
                raise ValidationError("N° de période invalide.")

    @api.depends('fiscal_year', 'period', 'period_number')
    def _compute_dates(self):
        for rec in self:
            y = rec.fiscal_year or fields.Date.context_today(rec).year
            if rec.period == 'month':
                start = fields.Date.to_date('%s-%02d-01' % (y, rec.period_number or 1))
                end = fields.Date.end_of(start, 'month')
            elif rec.period == 'quarter':
                start = fields.Date.to_date('%s-%02d-01' % (y, 3 * ((rec.period_number or 1) - 1) + 1))
                end = fields.Date.end_of(start, 'quarter')
            else:
                start = fields.Date.to_date('%s-01-01' % y)
                end = fields.Date.to_date('%s-12-31' % y)
            rec.date_from, rec.date_to = start, end

    @api.depends('cost_center_id', 'category', 'date_from', 'date_to', 'amount', 'threshold')
    def _compute_actual(self):
        Line = self.env['account.analytic.line'].sudo()
        for rec in self:
            domain = [('account_id', '=', rec.cost_center_id.id), ('date', '>=', rec.date_from),
                      ('date', '<=', rec.date_to), ('amount', '<', 0)]
            if rec.category:
                domain.append(('tms_category', '=', rec.category))
            rec.actual = -sum(Line.search(domain).mapped('amount'))
            rec.gap = rec.amount - rec.actual
            rec.consumed_pct = 100.0 * rec.actual / rec.amount if rec.amount else 0.0
            rec.state = 'over' if rec.actual > rec.amount else ('warning' if rec.consumed_pct >= rec.threshold else 'ok')

    @api.model
    def _cron_budget_alerts(self):
        """Alertes de dépassement / approche de seuil (reprises dans le tableau de bord TMS)."""
        today = fields.Date.context_today(self)
        for bud in self.search([('date_from', '<=', today), ('date_to', '>=', today)]):
            if bud.state != 'ok':
                bud.message_post(body="Budget %s : %.0f %% consommé (%s)." % (
                    bud.name, bud.consumed_pct, dict(bud._fields['state'].selection)[bud.state]),
                    subtype_xmlid='mail.mt_comment')
                if not bud.activity_ids:
                    bud.activity_schedule('mail.mail_activity_data_todo', summary='Budget %s : %s' % (
                        bud.name, dict(bud._fields['state'].selection)[bud.state]),
                        user_id=self.env.ref('base.user_admin').id)

    def action_open_lines(self):
        self.ensure_one()
        domain = [('account_id', '=', self.cost_center_id.id), ('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        if self.category:
            domain.append(('tms_category', '=', self.category))
        return {'type': 'ir.actions.act_window', 'name': 'Réalisé', 'res_model': 'account.analytic.line',
                'view_mode': 'list,pivot', 'domain': domain}
