{
    'name': 'TMS - Maintenance des engins',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing/Maintenance',
    'summary': 'Chariots, transpalettes, groupes électrogènes : contrôles réglementaires, interventions, coûts par centre de coût',
    'description': 'Cahier des charges TMS Flotte v3.3 - §9 Maintenance des Engins.',
    'depends': ['tms_fleet', 'maintenance'],
    'data': [
        'security/ir.model.access.csv',
        'data/tms_equipment_data.xml',
        'views/tms_equipment_views.xml',
    ],
    'license': 'LGPL-3',
}
