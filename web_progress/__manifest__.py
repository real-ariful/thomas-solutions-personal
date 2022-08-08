{
    'name': "Dynamic Progress Bar",
    'summary': """Progress bar for operations that take more than 5 seconds.""",
    'description': """
        Adds dynamic progress bar and cancel button to gray waiting screen.
        Try to import some CSV file to any model to see it in action.
    """,
    'author': "Grzegorz Marczyński",
    'category': 'Productivity',
    'version': '15.0.1',
    'depends': ['web', 'bus', 'base_import' ],
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/progress_bar.xml',
        'static/src/xml/web_progress_menu.xml',
    ],
    'images': [
        'static/description/progress_bar_loading_compact.gif',
        'static/description/progress_bar_loading_cancelling.gif',
        'static/description/progress_bar_loading_systray.gif',
    ],
    'assets': {
        'web.assets_backend': [
            '/web_progress/static/src/js/loading.js',
            '/web_progress/static/src/js/progress_bar.js',
            '/web_progress/static/src/js/ajax.js',
            '/web_progress/static/src/js/progress_menu.js',
            '/web_progress/static/src/css/views.css'
        ],
    },
    "price": 0,
    "currency": "USD",
    "license": "LGPL-3",
    "support": "support@syncoria.com",
    "installable": True,
    "application": False,
    "auto_install": True,



}
