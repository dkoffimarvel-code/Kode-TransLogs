{
    'name': 'TMS - Contrôle de gestion',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Budgets par centre de coût, suivi budget vs réalisé, alertes de dépassement, analyse par catégorie',
    'description': 'Cahier des charges TMS Flotte v3.3 - §13 Contrôle de Gestion.',
    'depends': ['tms_fleet', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/tms_budget_data.xml',
        'views/tms_budget_views.xml',
    ],
    'license': 'LGPL-3',
}
