from datetime import timedelta

from odoo import api, fields, models

DOC_TYPES = [
    ('insurance', 'Assurance'),
    ('technical_inspection', 'Contrôle technique'),
    ('registration', 'Carte grise'),
    ('transport_license', 'Licence de transport'),
    ('driving_license', 'Permis de conduire'),
    ('medical', 'Visite médicale'),
    ('fimo_fco', 'FIMO / FCO'),
    ('adr', 'Habilitation ADR'),
    ('caces', 'CACES'),
    ('electrical', 'Habilitation électrique'),
    ('other', 'Autre'),
]


class TmsDocument(models.Model):
    _name = 'tms.document'
    _description = 'Document obligatoire / habilitation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_expiry'

    name = fields.Char('Référence', compute='_compute_name', store=True)
    doc_type = fields.Selection(DOC_TYPES, 'Type de document', required=True, default='insurance')
    reference = fields.Char('N° / référence')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Véhicule', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employé / conducteur', ondelete='cascade')
    date_obtained = fields.Date("Date d'obtention")
    date_expiry = fields.Date("Date d'expiration", required=True, tracking=True)
    reminder_days = fields.Integer('Rappel (jours avant expiration)', default=30)
    attachment = fields.Binary('Fichier', attachment=True)
    attachment_name = fields.Char('Nom du fichier')
    state = fields.Selection([('valid', 'Valide'), ('expiring', 'À renouveler'), ('expired', 'Expiré')],
                             compute='_compute_state', store=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _check_owner = models.Constraint(
        'CHECK(vehicle_id IS NOT NULL OR employee_id IS NOT NULL)',
        'Le document doit être rattaché à un véhicule ou à un employé.')

    @api.depends('doc_type', 'vehicle_id', 'employee_id', 'reference')
    def _compute_name(self):
        labels = dict(DOC_TYPES)
        for rec in self:
            owner = rec.vehicle_id.display_name or rec.employee_id.name or ''
            rec.name = '%s - %s' % (labels.get(rec.doc_type, ''), owner)

    @api.depends('date_expiry', 'reminder_days')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.date_expiry:
                rec.state = 'valid'
            elif rec.date_expiry < today:
                rec.state = 'expired'
            elif rec.date_expiry <= today + timedelta(days=rec.reminder_days):
                rec.state = 'expiring'
            else:
                rec.state = 'valid'

    @api.model
    def _cron_check_expiry(self):
        """Recalcule les états (dépendance à la date du jour) et planifie une activité d'alerte."""
        docs = self.search([('date_expiry', '!=', False)])
        docs._compute_state()
        todo = self.env.ref('mail.mail_activity_data_todo')
        manager_group = self.env.ref('tms_fleet.group_tms_manager')
        users = manager_group.user_ids[:1] or self.env.user
        for doc in docs.filtered(lambda d: d.state in ('expiring', 'expired')):
            if doc.activity_ids.filtered(lambda a: a.activity_type_id == todo):
                continue
            doc.activity_schedule(
                'mail.mail_activity_data_todo', date_deadline=doc.date_expiry,
                summary='Document à renouveler : %s' % doc.name,
                user_id=(doc.vehicle_id.manager_id.id or users.id))
