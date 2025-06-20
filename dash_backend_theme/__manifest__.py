{
    "name": "Dash Backend Theme",
    "description": "Modern and elegant backend theme",
    "summary": "Modern and elegant backend theme. Redefining the Odoo UI",
    "category": "Themes/Backend",
    'version': '18.3',
    'author': 'RMT Works',
    'website': "https://github.com/rmtworks",
    "depends": ["base", "web", "mail"],
    "assets": {
        'web._assets_primary_variables': {
            '/dash_backend_theme/static/src/scss/colors.scss',
            '/dash_backend_theme/static/src/scss/variables.scss',
        },

        "web.assets_backend": {
            '/dash_backend_theme/static/src/js/*.js',
            '/dash_backend_theme/static/src/scss/*.scss',
            '/dash_backend_theme/static/src/xml/*.xml',
        },
        'web.assets_backend_lazy': [
            'dash_backend_theme/static/src/views/**',
        ],
        "web.assets_frontend": {
            "/dash_backend_theme/static/src/scss/website/*.scss",
        }
    },
    "images": [
        "static/description/banner.png",
        "static/description/theme_screenshot.png",
    ],
    "license": "OPL-1",
    "installable": True,
    "application": False,
    "auto_install": False,
    'price': 31.99,
    'currency': 'USD'
}