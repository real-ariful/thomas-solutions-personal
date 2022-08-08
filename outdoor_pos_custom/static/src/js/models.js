odoo.define('outdoor_pos_custom.models', function (require) {

var models = require('point_of_sale.models');

models.load_fields('res.partner', ['property_supplier_payment_term_name']);
models.load_fields('pos.payment.method', ['hide_method']);

});
