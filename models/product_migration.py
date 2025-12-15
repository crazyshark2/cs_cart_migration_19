# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from .migration_base import MigrationBase

_logger = logging.getLogger(__name__)

class ProductMigration(models.Model):
    _name = 'cs.cart.product.migration'
    _description = 'CS-Cart Product Migration'
    _inherit = 'cs.cart.migration.base'
    
    def migrate_products(self, connection, lang_code='tr', batch_size=50, update_existing=True):
        """Migrate products from CS-Cart to Odoo"""
        import mysql.connector
        from mysql.connector import Error
        
        log = self._create_migration_log(connection, 'product')
        migrated_products = []
        
        try:
            conn = connection.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get query based on CS-Cart version
            query = self._get_cs_cart_query(connection.cs_cart_version, 'products')
            
            # Execute query
            if '%s' in query:
                cursor.execute(query, (lang_code,))
            else:
                cursor.execute(query)
            
            products = cursor.fetchall()
            log.total_records = len(products)
            self._update_migration_log(log, processed_records=0)
            
            # Pre-fetch all categories for mapping
            category_mapping = self._get_category_mapping(connection)
            
            for i, prod in enumerate(products, 1):
                try:
                    odoo_product = self._create_or_update_product(prod, category_mapping, update_existing)
                    if odoo_product:
                        migrated_products.append(odoo_product.id)
                        log.successful_records += 1
                    
                    log.processed_records = i
                    
                    # Batch commit
                    if i % batch_size == 0:
                        self.env.cr.commit()
                        _logger.info(f"Processed {i} products")
                
                except Exception as e:
                    self._handle_migration_error(log, e, prod.get('product_id', 'unknown'))
                    continue
            
            # Update connection
            connection.last_sync_date = fields.Datetime.now()
            
            # Update log
            self._update_migration_log(log, 
                status='completed' if log.failed_records == 0 else 'partial',
                details=f"Successfully migrated {len(migrated_products)} products"
            )
            
            _logger.info(f"Product migration completed: {len(migrated_products)} products")
            
        except Error as e:
            self._update_migration_log(log, 
                status='failed',
                error_message=f"Database error: {str(e)}"
            )
            raise UserError(_('Product migration failed: %s') % str(e))
        except Exception as e:
            self._update_migration_log(log, 
                status='failed',
                error_message=f"Unexpected error: {str(e)}"
            )
            raise UserError(_('Product migration failed: %s') % str(e))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
        
        return migrated_products
    
    def _get_category_mapping(self, connection):
        """Get mapping of CS-Cart category IDs to Odoo category IDs"""
        categories = self.env['product.category'].search([
            ('cs_cart_id', '!=', False)
        ])
        return {cat.cs_cart_id: cat.id for cat in categories}
    
    def _create_or_update_product(self, prod_data, category_mapping, update_existing):
        """Create or update a product in Odoo"""
        # Check if product already exists
        existing_product = self.env['product.template'].search([
            ('cs_cart_id', '=', prod_data['product_id'])
        ], limit=1)
        
        # Find category
        category_id = False
        if prod_data.get('category_id') and prod_data['category_id'] in category_mapping:
            category_id = category_mapping[prod_data['category_id']]
        else:
            # Use default category
            category_id = self.env.ref('product.product_category_all').id
        
        # Prepare product values
        product_vals = {
            'name': prod_data.get('product') or prod_data.get('name', 'Unnamed Product'),
            'default_code': prod_data.get('product_code') or '',
            'description': prod_data.get('full_description') or '',
            'description_sale': prod_data.get('short_description') or '',
            'categ_id': category_id,
            'type': 'product',
            'list_price': float(prod_data.get('list_price', 0) or 0),
            'standard_price': float(prod_data.get('price', 0) or 0),
            'weight': float(prod_data.get('weight', 0) or 0),
            'volume': float(prod_data.get('length', 0) or 0) * 
                     float(prod_data.get('width', 0) or 0) * 
                     float(prod_data.get('height', 0) or 0),
            'active': prod_data.get('status', 'A') == 'A',
            'cs_cart_id': prod_data['product_id'],
            'sale_ok': True,
            'purchase_ok': True,
        }
        
        # Handle existing product
        if existing_product:
            if update_existing:
                existing_product.write(product_vals)
                return existing_product
            else:
                return existing_product
        else:
            # Create new product
            return self.env['product.template'].create(product_vals)