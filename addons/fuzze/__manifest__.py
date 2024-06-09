# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# type: ignore
{
    "name": "fuzze",
    "version": "0.1",
    "category": "Hidden/Tests",
    "summary": "GUI fuzzing for Odoo",
    "description": """This modules provides a GUI fuzzing tool for Odoo. It depends on the Odoo tour tool.""",
    "depends": ["test_main_flows"],
    "post_init_hook": "_auto_install_enterprise_dependencies",
    "data": ["models/ir.model.access.csv"],
    "assets": {
        "web.assets_tests": [
            "fuzze/static/tests/tours/generated/*.js",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}
