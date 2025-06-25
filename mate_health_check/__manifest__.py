{
    'name': 'Health check',
    'category': 'Medical',
    'summary': 'Manage Medical Surgery related operations',
    'description': """
    Manage Medical Surgery related operations hospital management system medical
    """,
    'version': '1.0.4',
    'author': 'MateJSC',
    'license': 'OPL-1',
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',

        # views
        'views/department_view.xml',
        'views/package_view.xml',
        'views/group_sequence_view.xml',
        'views/patient_view.xml',

        # wizard
        'wizard/create_department_wizard.xml',
        'wizard/create_group_sequence_wizard.xml',
        'wizard/create_package_wizard.xml',

        # menu items
        'views/menu_item.xml',

        # data seeding
        'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/mate_health_check/static/src/components/**/*',
            '/mate_health_check/static/src/js/customSaveFormView.js',
        ],
    },
    'sequence': 1,
    'application': True,
}
