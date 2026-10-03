{
    'name': 'TMS - RH, Paie et Notes de frais',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': "Dossier du personnel, contrats, congés, éléments de paie, bulletins, notes de frais par centre de coût",
    'description': 'Cahier des charges TMS Flotte v3.3 - §10 Ressources Humaines, §11 Paie, §12 Notes de frais.',
    'depends': ['tms_fleet', 'hr', 'hr_holidays', 'hr_expense'],
    'data': [
        'security/ir.model.access.csv',
        'data/tms_hr_data.xml',
        'views/hr_employee_views.xml',
        'views/tms_payroll_views.xml',
        'views/hr_expense_views.xml',
    ],
    'license': 'LGPL-3',
}
