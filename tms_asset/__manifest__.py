{
    'name': 'TMS - Immobilisations',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Registre des immobilisations, amortissements, cessions ; fiche créée automatiquement pour chaque véhicule',
    'description': 'Cahier des charges TMS Flotte v3.3 - §8 Immobilisations.',
    'depends': ['tms_fleet', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/tms_asset_data.xml',
        'views/tms_asset_views.xml',
    ],
    'license': 'LGPL-3',
}
