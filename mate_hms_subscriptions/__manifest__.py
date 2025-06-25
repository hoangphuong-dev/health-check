{
    'name': 'Mate HMS Package Management',
    'category': 'Medical',
    'summary': 'Manage Medical Surgery related operations',
    'description': """
    Manage Medical Surgery related operations hospital management system medical ACS HMS
    """,
    'version': '1.0.4',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'www.almightycs.com',
    'license': 'OPL-1',
    'depends': ['mate_hms'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/data.xml',
        'views/package_view.xml',
        'views/subscriptions_view.xml',
        'views/patient_view.xml',
        'views/menu_item.xml',
        'views/appointment_view.xml',
        'views/res_config_settings_views.xml',
        'wizard/handle_consumed_services.xml',
        'wizard/hanlde_upload_package.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/mate_hms_subscriptions/static/src/js/*.js',
            '/mate_hms_subscriptions/static/src/components/**/*',
        ],
    },
    'images': [
        'static/description/hms_surgery_almightycs_odoo_cover.jpg',
    ],
    'sequence': 1,
    'application': True,
    'price': 36,
    'currency': 'USD',
}
