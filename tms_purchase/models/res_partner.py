from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    tms_supplier_type = fields.Selection([
        ('garage', 'Garage'), ('dealer', 'Concessionnaire'), ('station', 'Station-service'),
        ('rental', 'Loueur de matériel'), ('other', 'Autre')], 'Type de fournisseur (TMS)')
    tms_supplier_rating = fields.Selection([('0', 'Non évalué'), ('1', 'Faible'), ('2', 'Correct'),
                                            ('3', 'Bon'), ('4', 'Excellent')], 'Évaluation', default='0')
