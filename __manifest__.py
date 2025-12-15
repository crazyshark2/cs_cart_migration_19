# -*- coding: utf-8 -*-
{
    'name': 'CS-Cart to Odoo 19 Migration',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'CS-Cart verilerini Odoo 19\'a aktarın',
    'description': """
        CS-Cart 4.x veritabanından Odoo 19'a ürün, kategori, 
        müşteri ve tedarikçi verilerini aktarın.
        
        Özellikler:
        - CS-Cart 4.0 - 4.15+ tüm versiyonları destekler
        - Multi-Vendor (Mve) desteği
        - Batch işleme ile performans optimizasyonu
        - Hata loglama ve geri alma
        - Detaylı raporlama
    """,
    'author': 'Odoo Migration Expert',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale',
        'purchase',
        'stock',
        'account',
        'contacts',
    ],
    'external_dependencies': {
        'python': ['mysql.connector', 'pymysql'],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/default_data.xml',
        'views/config_views.xml',
        'views/wizard_views.xml',
        'views/menu_views.xml',
        'report/migration_report.xml',
    ],
    'demo': [],
    'assets': {
        'web.assets_backend': [
            'cs_cart_migration_19/static/src/js/migration_progress.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 0,
    'currency': 'EUR',
}