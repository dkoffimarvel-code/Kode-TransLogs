{
    'name': 'TMS - Achats et stock de pièces',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': "Demandes d'achat, commandes, réceptions, sorties de stock imputées par centre de coût",
    'description': 'Cahier des charges TMS Flotte v3.3 - §6 Achats et Gestion de Stock.',
    'depends': ['tms_fleet', 'purchase', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/tms_purchase_data.xml',
        'views/tms_purchase_views.xml',
    ],
    'license': 'LGPL-3',
}
