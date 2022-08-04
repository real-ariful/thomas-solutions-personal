//note:  this widget js file and all aspects related to it are not use and were for research only
//left in the system for future use,
odoo.define('thomasfleet.utility_field', function(require)


"use strict";
var core = require('web.core');
var qweb = require('web.QWeb');

var AbstractField = require('web.AbstractField');
var fieldRegistry = require('web.field_registry');


var utility_field = AbstractField.extend({
    className: 'oe_utility_field',
    template : 'UtilityField',
    xmlDependencies:'/thomasfleet/'

    init: function() {
        this._super.apply(this, arguments);
        this.set("value", "");


    },
    start: function() {
        this.on("change:effective_readonly", this, function(){
            this.render_value();

        });

        return this._super();
    },
    _render: function(){
        console.log("in _rendoer");
        this.set("value", "SUPER PPPU");
        this.renderElement();
    },
    render:function(){
        this.$el.text("ALL RENDER MODES");
    },
    render_value: function() {
        console.log("In render value");
        this.$el.text("Test VALUE");
    },
    test: function(){
        return "TEST VALUE"
    },
    getValue:function(){
        return "test getValue";
    },
     _getValue: function () {
        var value = this.getValue();
        return value +"YIPPEE SKIPPEE";
    }

});


fieldRegistry.add('utility_field', utility_field);

 return {
      utility_field: utility_field
    };

});