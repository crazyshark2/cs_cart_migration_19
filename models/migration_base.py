# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class CsCartMigrationLog(models.Model):
    _name = 'cs.cart.migration.log'
    _description = 'CS-Cart Migration Log'
    _order = 'create_date desc'
    _rec_name = 'migration_type'
    
    connection_id = fields.Many2one(
        'cs.cart.connection',
        string='Connection',
        required=True,
        ondelete='cascade'
    )
    
    migration_type = fields.Selection([
        ('category', 'Categories'),
        ('product', 'Products'),
        ('customer', 'Customers'),
        ('supplier', 'Suppliers'),
        ('order', 'Orders'),
        ('full', 'Full Migration'),
    ], string='Migration Type', required=True)
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partial Success'),
    ], string='Status', default='draft')
    
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')
    duration = fields.Float(string='Duration (seconds)', compute='_compute_duration')
    
    total_records = fields.Integer(string='Total Records')
    processed_records = fields.Integer(string='Processed Records')
    successful_records = fields.Integer(string='Successful Records')
    failed_records = fields.Integer(string='Failed Records')
    
    error_message = fields.Text(string='Error Message')
    details = fields.Text(string='Migration Details')
    
    # Related fields for quick access
    product_count = fields.Integer(string='Products Migrated', compute='_compute_counts')
    category_count = fields.Integer(string='Categories Migrated', compute='_compute_counts')
    customer_count = fields.Integer(string='Customers Migrated', compute='_compute_counts')
    
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for log in self:
            if log.start_date and log.end_date:
                start = fields.Datetime.from_string(log.start_date)
                end = fields.Datetime.from_string(log.end_date)
                log.duration = (end - start).total_seconds()
            else:
                log.duration = 0.0
    
    def _compute_counts(self):
        # This would be implemented to count actual migrated records
        pass
    
    def action_view_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Migration Details'),
            'res_model': 'cs.cart.migration.log',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }
    
    def action_retry(self):
        self.ensure_one()
        # Implement retry logic
        pass

class MigrationBase(models.AbstractModel):
    _name = 'cs.cart.migration.base'
    _description = 'CS-Cart Migration Base Class'
    
    def _create_migration_log(self, connection, migration_type, total_records=0):
        """Create a new migration log entry"""
        return self.env['cs.cart.migration.log'].create({
            'connection_id': connection.id,
            'migration_type': migration_type,
            'status': 'in_progress',
            'start_date': fields.Datetime.now(),
            'total_records': total_records,
        })
    
    def _update_migration_log(self, log, **kwargs):
        """Update migration log with progress"""
        if 'processed_records' in kwargs:
            log.processed_records = kwargs['processed_records']
        if 'successful_records' in kwargs:
            log.successful_records = kwargs['successful_records']
        if 'failed_records' in kwargs:
            log.failed_records = kwargs['failed_records']
        if 'status' in kwargs:
            log.status = kwargs['status']
        if 'error_message' in kwargs:
            log.error_message = kwargs['error_message']
        if 'details' in kwargs:
            log.details = kwargs['details']
        
        # If completed or failed, set end date
        if kwargs.get('status') in ['completed', 'failed', 'partial']:
            log.end_date = fields.Datetime.now()
    
    def _handle_migration_error(self, log, error, record_id=None):
        """Handle migration errors gracefully"""
        _logger.error(f"Migration error for record {record_id}: {str(error)}")
        
        if log:
            log.failed_records += 1
            error_details = f"Record ID: {record_id}\nError: {str(error)}\n"
            if log.error_message:
                log.error_message += "\n---\n" + error_details
            else:
                log.error_message = error_details
        
        # You can implement email notification here if needed
    
    def _batch_commit(self, batch_size=100, current_count=0):
        """Commit in batches to avoid memory issues"""
        if current_count % batch_size == 0:
            self.env.cr.commit()
            _logger.info(f"Committed batch: {current_count} records")
    
    def _get_cs_cart_query(self, version, query_type):
        """Get appropriate SQL query based on CS-Cart version"""
        queries = {
            '4.0': {
                'categories': """
                    SELECT category_id, parent_id, category, 
                           description, position, status
                    FROM cscart_categories
                    WHERE status = 'A'
                    ORDER BY parent_id, position
                """,
                'products': """
                    SELECT p.product_id, p.product_code, p.product, 
                           p.full_description, p.short_description, p.status,
                           p.list_price, p.price, p.amount, p.weight,
                           p.length, p.width, p.height, p.timestamp,
                           pc.category_id
                    FROM cscart_products p
                    LEFT JOIN cscart_products_categories pc ON p.product_id = pc.product_id
                    WHERE p.status = 'A'
                """
            },
            '4.10': {
                'categories': """
                    SELECT c.category_id, c.parent_id, cd.category, 
                           cd.description, c.position, c.status
                    FROM cscart_categories c
                    LEFT JOIN cscart_category_descriptions cd 
                        ON c.category_id = cd.category_id AND cd.lang_code = %s
                    WHERE c.status = 'A'
                    ORDER BY c.parent_id, c.position
                """,
                'products': """
                    SELECT p.product_id, p.product_code, pd.product, 
                           pd.full_description, pd.short_description, p.status,
                           p.list_price, p.price, p.amount, p.weight,
                           p.length, p.width, p.height, p.timestamp,
                           pi.detailed_id as image_id, pi.image_path,
                           pc.category_id
                    FROM cscart_products p
                    LEFT JOIN cscart_product_descriptions pd 
                        ON p.product_id = pd.product_id AND pd.lang_code = %s
                    LEFT JOIN cscart_images pi 
                        ON p.product_id = pi.object_id AND pi.object_type = 'product'
                    LEFT JOIN cscart_products_categories pc 
                        ON p.product_id = pc.product_id AND pc.link_type = 'M'
                    WHERE p.status = 'A'
                """
            },
            'mve': {
                'suppliers': """
                    SELECT u.user_id, u.email, u.firstname, u.lastname,
                           u.phone, u.fax, u.company, u.address, u.city,
                           u.state, u.country, u.zipcode, u.status,
                           c.company as vendor_name, c.status as vendor_status
                    FROM cscart_users u
                    LEFT JOIN cscart_companies c ON u.company_id = c.company_id
                    WHERE u.user_type = 'V' AND u.status = 'A'
                """
            }
        }
        
        # Return query for the specific version or fallback to 4.0
        if version in queries and query_type in queries[version]:
            return queries[version][query_type]
        elif query_type in queries['4.0']:
            return queries['4.0'][query_type]
        else:
            raise ValueError(f"Query type '{query_type}' not found for version '{version}'")