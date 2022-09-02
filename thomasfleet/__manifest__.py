# -*- coding: utf-8 -*-
{
    'name': "Thomas Solutions Fleet Management",
    'summary': """Extend and customize Odoo Fleet module to meet Thomas Solutions requirements""",
    'description': """Extend and customize Odoo Fleet module to meet Thomas Solutions requirements""",
    'author': "Andrew Bates[Dev], AZM Ariful Haque Real[Upgrade]",
    'website': "https://www.syncoria.com",
    'category': 'Human Resources/Fleet',
    'version': '15.0.1',
    'depends': ['base', 'fleet', 'account', 'web', 'account_fleet'],
    'data': [
        'security/thomasfleet_security.xml',
        'security/ir.model.access.csv',
        'views/message_views.xml',
        'views/views.xml',
        'views/lease_views.xml',
        'views/customer_views.xml',
        'views/invoice_views.xml',
        'views/templates.xml',
        'views/product_views.xml',
        'report/lease_print_template.xml',
        'report/lease_printout.xml',
        'report/invoice_report_template.xml',
        ########################################
        # 'report/custom_external_layout.xml',
        # 'report/report_invoice_templates.xml',
        ####################################
        # Data
        'data/fleet.vehicle.state.csv',
        'data/thomasfleet.lease_status.csv',
        'data/thomasfleet.location.csv',
        'data/thomasfleet.floormaterial.csv',
        'data/thomasfleet.fueltype.csv',
        'data/thomasfleet.seatmaterial.csv',
        'data/thomasfleet.asset_class.csv',
        'data/thomasfleet.insurance_class.csv',
        'data/fleet.vehicle.model.brand.csv',
        'data/fleet.vehicle.model.csv',
        'data/thomasfleet.trim.csv',
        'data/thomasfleet.inclusions.csv',
        'data/thomasfleet.accessory_type.csv'
    ],
    'assets': {
        'web.assets_backend': [
            'thomasfleet/static/src/less/variables.less',
            'thomasfleet/static/src/less/styles.less',
            'thomasfleet/static/src/less/report.less'
        ],
        'web.report_assets_common': [
            'thomasfleet/static/src/less/styles.less',
            'thomasfleet/static/src/less/report.less',
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
