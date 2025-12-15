# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class CsCartMigrationWizard(models.TransientModel):
    _name = 'cs.cart.migration.wizard'
    _description = 'CS-Cart Migration Wizard'
    
    # Basic Information
    name = fields.Char(string='Migration Name', default=lambda self: _('Migration %s') % fields.Datetime.now())
    connection_id = fields.Many2one(
        'cs.cart.connection',
        string='CS-Cart Connection',
        required=True,
        domain=[('active', '=', True)]
    )
    
    cs_cart_version = fields.Selection(related='connection_id.cs_cart_version', readonly=True)
    
    # Migration Options
    import_categories = fields.Boolean(string='Import Categories', default=True)
    import_products = fields.Boolean(string='Import Products', default=True)
    import_customers = fields.Boolean(string='Import Customers', default=True)
    import_suppliers = fields.Boolean(string='Import Suppliers', default=False)
    
    # Advanced Options
    update_existing = fields.Boolean(
        string='Update Existing Records',
        default=True,
        help="Update records that already exist in Odoo"
    )
    
    create_missing_categories = fields.Boolean(
        string='Create Missing Categories',
        default=True,
        help="Create categories if they don't exist in Odoo"
    )
    
    import_images = fields.Boolean(
        string='Import Product Images',
        default=False,
        help="Import product images from CS-Cart (requires image paths)"
    )
    
    import_prices = fields.Boolean(
        string='Import Prices',
        default=True,
        help="Import product prices and costs"
    )
    
    import_inventory = fields.Boolean(
        string='Import Inventory',
        default=False,
        help="Import product quantities (requires stock module)"
    )
    
    # Performance Options
    batch_size = fields.Integer(
        string='Batch Size',
        default=100,
        help="Number of records to process in each batch",
        required=True
    )
    
    language_code = fields.Char(
        string='Language Code',
        default='tr',
        help="Language code for product descriptions",
        required=True
    )
    
    # Status Fields
    state = fields.Selection([
        ('draft', 'Draft'),
        ('config', 'Configuration'),
        ('progress', 'In Progress'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ], string='Status', default='draft', readonly=True)
    
    progress = fields.Float(string='Progress', default=0.0)
    current_operation = fields.Char(string='Current Operation')
    log_message = fields.Text(string='Log Messages')
    
    # Results
    categories_imported = fields.Integer(string='Categories Imported', readonly=True)
    products_imported = fields.Integer(string='Products Imported', readonly=True)
    customers_imported = fields.Integer(string='Customers Imported', readonly=True)
    suppliers_imported = fields.Integer(string='Suppliers Imported', readonly=True)
    
    start_time = fields.Datetime(string='Start Time', readonly=True)
    end_time = fields.Datetime(string='End Time', readonly=True)
    duration = fields.Char(string='Duration', compute='_compute_duration', readonly=True)
    
    @api.constrains('batch_size')
    def _check_batch_size(self):
        for record in self:
            if record.batch_size < 1:
                raise ValidationError(_('Batch size must be at least 1'))
            if record.batch_size > 1000:
                raise ValidationError(_('Batch size cannot exceed 1000'))
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                start = fields.Datetime.from_string(record.start_time)
                end = fields.Datetime.from_string(record.end_time)
                delta = end - start
                seconds = delta.total_seconds()
                
                if seconds < 60:
                    record.duration = f"{seconds:.1f} seconds"
                elif seconds < 3600:
                    minutes = seconds / 60
                    record.duration = f"{minutes:.1f} minutes"
                else:
                    hours = seconds / 3600
                    record.duration = f"{hours:.1f} hours"
            else:
                record.duration = ''
    
    def action_start_migration(self):
        """Start the migration process"""
        self.ensure_one()
        
        # Validate inputs
        if not any([self.import_categories, self.import_products, 
                   self.import_customers, self.import_suppliers]):
            raise UserError(_('Please select at least one data type to import'))
        
        # Start migration in background job
        self._start_background_migration()
        
        # Return action to show progress
        return {
            'type': 'ir.actions.act_window',
            'name': _('Migration Progress'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'progress_mode': True},
        }
    
    def _start_background_migration(self):
        """Start migration in background"""
        self.write({
            'state': 'progress',
            'start_time': fields.Datetime.now(),
            'progress': 0,
            'log_message': _('Migration started...\n'),
        })
        
        # Create background job
        self.with_delay()._run_migration_job()
    
    def _run_migration_job(self):
        """Background job for migration"""
        try:
            total_steps = sum([
                1 if self.import_categories else 0,
                1 if self.import_products else 0,
                1 if self.import_customers else 0,
                1 if self.import_suppliers else 0,
            ])
            
            current_step = 0
            
            # Import categories
            if self.import_categories:
                current_step += 1
                self._update_progress(current_step, total_steps, _('Importing categories...'))
                categories = self._import_categories()
                self.categories_imported = len(categories)
                self._add_log_message(_('Imported %d categories\n') % len(categories))
            
            # Import products
            if self.import_products:
                current_step += 1
                self._update_progress(current_step, total_steps, _('Importing products...'))
                products = self._import_products()
                self.products_imported = len(products)
                self._add_log_message(_('Imported %d products\n') % len(products))
            
            # Import customers
            if self.import_customers:
                current_step += 1
                self._update_progress(current_step, total_steps, _('Importing customers...'))
                customers = self._import_customers()
                self.customers_imported = len(customers)
                self._add_log_message(_('Imported %d customers\n') % len(customers))
            
            # Import suppliers
            if self.import_suppliers and self.cs_cart_version == 'mve':
                current_step += 1
                self._update_progress(current_step, total_steps, _('Importing suppliers...'))
                suppliers = self._import_suppliers()
                self.suppliers_imported = len(suppliers)
                self._add_log_message(_('Imported %d suppliers\n') % len(suppliers))
            
            # Complete migration
            self.write({
                'state': 'completed',
                'end_time': fields.Datetime.now(),
                'progress': 100,
            })
            
            self._add_log_message(_('\nMigration completed successfully!\n'))
            self._add_log_message(_('Total imported:\n'))
            self._add_log_message(_('- Categories: %d\n') % self.categories_imported)
            self._add_log_message(_('- Products: %d\n') % self.products_imported)
            self._add_log_message(_('- Customers: %d\n') % self.customers_imported)
            if self.cs_cart_version == 'mve':
                self._add_log_message(_('- Suppliers: %d\n') % self.suppliers_imported)
            
        except Exception as e:
            _logger.error(f"Migration failed: {str(e)}", exc_info=True)
            self.write({
                'state': 'error',
                'end_time': fields.Datetime.now(),
            })
            self._add_log_message(_('\n❌ Migration failed:\n%s\n') % str(e))
            raise
    
    def _import_categories(self):
        """Import categories from CS-Cart"""
        migration = self.env['cs.cart.category.migration']
        return migration.migrate_categories(
            connection=self.connection_id,
            lang_code=self.language_code,
            batch_size=self.batch_size,
            update_existing=self.update_existing
        )
    
    def _import_products(self):
        """Import products from CS-Cart"""
        migration = self.env['cs.cart.product.migration']
        return migration.migrate_products(
            connection=self.connection_id,
            lang_code=self.language_code,
            batch_size=self.batch_size,
            update_existing=self.update_existing
        )
    
    def _import_customers(self):
        """Import customers from CS-Cart"""
        migration = self.env['cs.cart.partner.migration']
        return migration.migrate_customers(
            connection=self.connection_id,
            batch_size=self.batch_size,
            update_existing=self.update_existing
        )
    
    def _import_suppliers(self):
        """Import suppliers from CS-Cart"""
        migration = self.env['cs.cart.partner.migration']
        return migration.migrate_suppliers(
            connection=self.connection_id,
            batch_size=self.batch_size,
            update_existing=self.update_existing
        )
    
    def _update_progress(self, current, total, operation):
        """Update progress and current operation"""
        progress = (current / total) * 100 if total > 0 else 0
        self.write({
            'progress': progress,
            'current_operation': operation,
        })
        self.env.cr.commit()  # Commit progress to database
    
    def _add_log_message(self, message):
        """Add message to log"""
        if self.log_message:
            self.log_message += message
        else:
            self.log_message = message
        self.env.cr.commit()
    
    def action_retry(self):
        """Retry failed migration"""
        self.write({
            'state': 'draft',
            'progress': 0,
            'log_message': '',
            'start_time': False,
            'end_time': False,
        })
        return self.action_start_migration()
    
    def action_cancel(self):
        """Cancel migration"""
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}