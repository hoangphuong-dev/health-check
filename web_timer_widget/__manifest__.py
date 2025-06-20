{
    'name': "Web Timer Widget",
    'category': "web",
    'version': "18.0.1.0.0",
    'summary': """Add timer widget on web view.""",
    'description': """This module widget which allows you to set timer on any field by passing your start and end date as parameter. start stop timer working time""",
    "website": 'https://www.almightycs.com',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'license': 'OPL-1',
    'depends': ['base', 'web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'web_timer_widget/static/src/js/acs_timer.js',
            'web_timer_widget/static/src/js/acs_timer.xml',
        ]
    },
    'images': [
        'static/description/timer.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    "price": 14,
    "currency": "USD",
}