# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from .migration_base import MigrationBase

_logger = logging.getLogger(__name__)

class CategoryMigration(models.Model):
    _name = 'cs.cart.category.migration'
    _description = 'CS-Cart Category Migration'
    _inherit = 'cs.cart.migration.base'
    
    def migrate_categories(self, connection, lang_code='tr', batch_size=100, update_existing=True):
        """Migrate categories from CS-Cart to Odoo"""
        import mysql.connector
        from mysql.connector import Error
        
        log = self._create_migration_log(connection, 'category')
        migrated_categories = []
        category_mapping = {}  # CS-Cart ID -> Odoo ID mapping
        
        try:
            conn = connection.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get query based on CS-Cart version
            query = self._get_cs_cart_query(connection.cs_cart_version, 'categories')
            
            # Execute query with parameters if needed
            if '%s' in query:
                cursor.execute(query, (lang_code,))
            else:
                cursor.execute(query)
            
            categories = cursor.fetchall()
            log.total_records = len(categories)
            self._update_migration_log(log, processed_records=0)
            
            for i, cat in enumerate(categories, 1):
                try:
                    odoo_category = self._create_or_update_category(cat, category_mapping, update_existing)
                    if odoo_category:
                        category_mapping[cat['category_id']] = odoo_category.id
                        migrated_categories.append(odoo_category.id)
                        log.successful_records += 1
                    
                    log.processed_records = i
                    
                    # Batch commit
                    if i % batch_size == 0:
                        self.env.cr.commit()
                        _logger.info(f"Processed {i} categories")
                
                except Exception as e:
                    self._handle_migration_error(log, e, cat.get('category_id', 'unknown'))
                    continue
            
            # Update connection
            connection.last_sync_date = fields.Datetime.now()
            
            # Update log
            self._update_migration_log(log, 
                status='completed' if log.failed_records == 0 else 'partial',
                details=f"Successfully migrated {len(migrated_categories)} categories"
            )
            
            _logger.info(f"Category migration completed: {len(migrated_categories)} categories")
            
        except Error as e:
            self._update_migration_log(log, 
                status='failed',
                error_message=f"Database error: {str(e)}"
            )
            raise UserError(_('Category migration failed: %s') % str(e))
        except Exception as e:
            self._update_migration_log(log, 
                status='failed',
                error_message=f"Unexpected error: {str(e)}"
            )
            raise UserError(_('Category migration failed: %s') % str(e))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
        
        return migrated_categories
    
    def _create_or_update_category(self, cat_data, category_mapping, update_existing):
        """Create or update a category in Odoo"""
        # Find parent category
        parent_id = False
        if cat_data.get('parent_id') and cat_data['parent_id'] in category_mapping:
            parent_id = category_mapping[cat_data['parent_id']]
        
        # Check if category already exists
        existing_category = self.env['product.category'].search([
            ('cs_cart_id', '=', cat_data['category_id'])
        ], limit=1)
        
        # Prepare category values
        category_vals = {
            'name': cat_data.get('category') or cat_data.get('name', 'Unnamed Category'),
            'parent_id': parent_id,
            'description': cat_data.get('description') or '',
            'cs_cart_id': cat_data['category_id'],
            'active': cat_data.get('status', 'A') == 'A',
        }
        
        # Handle existing category
        if existing_category:
            if update_existing:
                existing_category.write(category_vals)
                return existing_category
            else:
                return existing_category
        else:
            # Create new category
            return self.env['product.category'].create(category_vals)