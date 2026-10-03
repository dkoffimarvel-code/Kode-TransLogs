from odoo import api, fields, models


class TmsReportSchedule(models.Model):
    _name = 'tms.report.schedule'
    _description = 'Rapport périodique programmé'

    name = fields.Char('Nom du rapport', required=True)
    report_type = fields.Selection([('fleet', 'Synthèse flotte'), ('cost', 'Coûts d\'exploitation'),
                                    ('compliance', 'Conformité documentaire'), ('safety', 'Sécurité conducteurs')],
                                   'Type de rapport', required=True, default='fleet')
    periodicity = fields.Selection([('daily', 'Quotidienne'), ('weekly', 'Hebdomadaire'), ('monthly', 'Mensuelle')],
                                   'Périodicité', required=True, default='weekly')
    export_format = fields.Selection([('html', 'Corps du mail'), ('csv', 'CSV')], 'Format', default='html')
    recipient_ids = fields.Many2many('res.partner', string='Destinataires')
    last_sent = fields.Datetime(readonly=True)
    active = fields.Boolean(default=True)

    def _build_lines(self):
        self.ensure_one()
        V = self.env['fleet.vehicle']
        if self.report_type == 'fleet':
            return [(s[1], V.search_count([('tms_status', '=', s[0])])) for s in V._fields['tms_status'].selection]
        if self.report_type == 'cost':
            return [(v.display_name, round(v.total_cost, 2)) for v in V.search([]).sorted('total_cost', reverse=True)[:20]]
        if self.report_type == 'compliance':
            docs = self.env['tms.document'].search([('state', '!=', 'valid')])
            return [(d.name, '%s (%s)' % (d.date_expiry, d.state)) for d in docs]
        emp = self.env['hr.employee'].search([('is_driver', '=', True)]).sorted('safety_score')
        return [(e.name, e.safety_score) for e in emp[:20]]

    def _send(self):
        for rep in self:
            lines = rep._build_lines()
            body = '<h3>%s</h3><table>%s</table>' % (
                rep.name, ''.join('<tr><td>%s</td><td>%s</td></tr>' % (a, b) for a, b in lines))
            if rep.recipient_ids:
                self.env['mail.mail'].sudo().create({
                    'subject': rep.name, 'body_html': body,
                    'recipient_ids': [(6, 0, rep.recipient_ids.ids)],
                }).send()
            rep.last_sent = fields.Datetime.now()

    def action_send_now(self):
        self._send()

    @api.model
    def _cron_send_reports(self):
        now = fields.Datetime.now()
        days = {'daily': 1, 'weekly': 7, 'monthly': 30}
        for rep in self.search([]):
            if not rep.last_sent or (now - rep.last_sent).days >= days[rep.periodicity]:
                rep._send()
