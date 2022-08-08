# -*- coding: utf-8 -*-
{
    'name': "POS Custom Module for Outdoor Supplies",
    'summary': """POS Custom Module for Outdoor Supplies""",
    'description': """POS Custom Module for Outdoor Supplies""",
    'author': "AZM Ariful Haque Real",
    'website': "https://www.syncoria.com",
    'category': 'POS',
    'version': '15.0.1',
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_payment_method.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'outdoor_pos_custom/static/src/js/models.js',
        ],
        'web.assets_qweb': [
            'outdoor_pos_custom/static/src/xml/**/*',
        ],
    },
    "price": 0,
    "currency": "USD",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "installable": True,
    "application": False,
    "auto_install": False,

}