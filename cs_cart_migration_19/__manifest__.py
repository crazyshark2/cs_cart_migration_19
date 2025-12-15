# -*- coding: utf-8 -*-
{
    'name': "CS-Cart Migration Tool",
    'summary': """Migrate data from CS-Cart to Odoo 19""",
    'description': """
        This module allows you to migrate products, categories, customers,
        orders and other data from CS-Cart e-commerce platform to Odoo 19.
        Features include:
        - Configurable connection to CS-Cart database
        - Selective migration of data
        - Migration progress tracking
        - Error logging and reporting
    """,
    'author': "Your Company",
    'website': "https://www.yourcompany.com",
    'category': 'Tools',
    'version': '1.0.0',
    'license': 'LGPL-3',

    # Dependencies
    'depends': [
        'base',
        'sale',
        'product',
        'stock',
        'website_sale',
    ],

    # Data files to load
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/default_data.xml',
        'views/config_views.xml',
        'views/wizard_views.xml',
        'views/menu_views.xml',
    ],

    # QWeb templates
    'qweb': [],

    # Static files
    'css': [],
    'js': [],

    # Demo data
    'demo': [],

    # Images
    'images': [
        'static/description/icon.png',
        'static/description/banner.png',
    ],

    # Odoo version compatibility
    'installable': True,
    'application': True,
    'auto_install': False,
}
