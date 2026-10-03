from odoo import api, fields, models

TMS_CATEGORIES = [
    ('fuel', 'Carburant'), ('maintenance', 'Maintenance'), ('incident', 'Incidents'),
    ('purchase', 'Achats'), ('salary', 'Salaires'), ('expense', 'Notes de frais'),
    ('depreciation', 'Amortissements'), ('other', 'Autre'),
]


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    tms_category = fields.Selection(TMS_CATEGORIES, 'Catégorie de dépense TMS')

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Lignes issues de la comptabilité (factures fournisseurs, notes de frais) : catégorisation par défaut
        for line in lines.filtered(lambda l: not l.tms_category and l.move_line_id):
            ml = line.move_line_id
            if ml.move_id.is_purchase_document():
                line.tms_category = 'purchase'
        return lines


class TmsCostMixin(models.AbstractModel):
    """Imputation analytique par centre de coût au niveau du dossier (§5.5, §13.2).

    Le centre de coût du dossier est proposé par défaut depuis le véhicule / le
    conducteur / l'employé mais peut être modifié. Chaque dossier valorisé
    génère une ligne analytique reprise par le Contrôle de Gestion.
    """
    _name = 'tms.cost.mixin'
    _description = 'Imputation par centre de coût'

    cost_center_id = fields.Many2one(
        'account.analytic.account', string='Centre de coût',
        domain="[('plan_id.name', '=', 'Centres de coût')]", tracking=True)
    analytic_line_id = fields.Many2one('account.analytic.line', copy=False, readonly=True)

    # --- à surcharger -------------------------------------------------
    def _tms_cost_amount(self):
        return 0.0

    def _tms_cost_date(self):
        return fields.Date.context_today(self)

    def _tms_cost_category(self):
        return 'other'

    def _tms_cost_label(self):
        return self.display_name

    def _tms_cost_active(self):
        return True

    # ------------------------------------------------------------------
    def _sync_analytic_line(self):
        for rec in self:
            line = rec.analytic_line_id
            amount = rec._tms_cost_amount()
            if not (rec.cost_center_id and amount and rec._tms_cost_active()):
                if line:
                    line.unlink()
                continue
            vals = {
                'name': rec._tms_cost_label(),
                'account_id': rec.cost_center_id.id,
                'amount': -abs(amount),
                'date': rec._tms_cost_date(),
                'tms_category': rec._tms_cost_category(),
                'company_id': rec.env.company.id,
            }
            if line:
                line.write(vals)
            else:
                rec.analytic_line_id = self.env['account.analytic.line'].sudo().create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        recs._sync_analytic_line()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('tms_no_sync'):
            self.with_context(tms_no_sync=True)._sync_analytic_line()
        return res

    def unlink(self):
        self.analytic_line_id.sudo().unlink()
        return super().unlink()
