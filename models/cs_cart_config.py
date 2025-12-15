# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class CsCartConnection(models.Model):
    _name = 'cs.cart.connection'
    _description = 'CS-Cart Database Connection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string='Connection Name',
        required=True,
        tracking=True
    )
    
    host = fields.Char(
        string='Host',
        required=True,
        default='localhost',
        help="CS-Cart database server hostname or IP address",
        tracking=True
    )
    
    port = fields.Integer(
        string='Port',
        required=True,
        default=3306,
        tracking=True
    )
    
    database = fields.Char(
        string='Database Name',
        required=True,
        help="CS-Cart database name",
        tracking=True
    )
    
    username = fields.Char(
        string='Username',
        required=True,
        default='root',
        tracking=True
    )
    
    password = fields.Char(
        string='Password',
        required=True,
        tracking=True
    )
    
    cs_cart_version = fields.Selection([
        ('auto', 'Auto Detect'),
        ('4.0', 'CS-Cart 4.0.x'),
        ('4.3', 'CS-Cart 4.3.x'),
        ('4.5', 'CS-Cart 4.5.x'),
        ('4.6', 'CS-Cart 4.6.x'),
        ('4.7', 'CS-Cart 4.7.x'),
        ('4.8', 'CS-Cart 4.8.x'),
        ('4.9', 'CS-Cart 4.9.x'),
        ('4.10', 'CS-Cart 4.10.x'),
        ('4.11', 'CS-Cart 4.11.x'),
        ('4.12', 'CS-Cart 4.12.x'),
        ('4.13', 'CS-Cart 4.13.x'),
        ('4.14', 'CS-Cart 4.14.x'),
        ('4.15', 'CS-Cart 4.15.x'),
        ('mve', 'Multi-Vendor Edition'),
    ], string='CS-Cart Version', default='auto', required=True)
    
    language_code = fields.Char(
        string='Default Language Code',
        default='tr',
        help="Default language code for product descriptions (tr, en, etc.)",
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )
    
    last_connection_test = fields.Datetime(
        string='Last Connection Test',
        readonly=True
    )
    
    last_sync_date = fields.Datetime(
        string='Last Sync Date',
        readonly=True
    )
    
    total_migrations = fields.Integer(
        string='Total Migrations',
        compute='_compute_migration_stats',
        store=True
    )
    
    last_migration_status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
        ('none', 'Not Started'),
    ], string='Last Migration Status', default='none')
    
    # Constraint methods
    @api.constrains('port')
    def _check_port(self):
        for record in self:
            if record.port < 1 or record.port > 65535:
                raise ValidationError(_("Port must be between 1 and 65535"))
    
    @api.constrains('host')
    def _check_host(self):
        for record in self:
            if not record.host or len(record.host.strip()) == 0:
                raise ValidationError(_("Host cannot be empty"))
    
    # Compute methods
    @api.depends('last_sync_date')
    def _compute_migration_stats(self):
        MigrationLog = self.env['cs.cart.migration.log']
        for connection in self:
            logs = MigrationLog.search([('connection_id', '=', connection.id)])
            connection.total_migrations = len(logs)
    
    # Action methods
    def action_test_connection(self):
        self.ensure_one()
        try:
            self._test_connection()
            self.last_connection_test = fields.Datetime.now()
            self.last_migration_status = 'success'
            
            # Auto-detect version if set to auto
            if self.cs_cart_version == 'auto':
                detected_version = self._detect_cs_cart_version()
                if detected_version:
                    self.cs_cart_version = detected_version
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Connection successful!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            self.last_migration_status = 'failed'
            raise UserError(_('Connection failed: %s') % str(e))
    
    def action_open_migration_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('CS-Cart Migration'),
            'res_model': 'cs.cart.migration.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_connection_id': self.id,
                'default_cs_cart_version': self.cs_cart_version,
            },
        }
    
    def action_view_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Migration Logs'),
            'res_model': 'cs.cart.migration.log',
            'view_mode': 'tree,form',
            'domain': [('connection_id', '=', self.id)],
            'context': {'default_connection_id': self.id},
        }
    
    # Private methods
    def _test_connection(self):
        """Test connection to CS-Cart database"""
        import mysql.connector
        from mysql.connector import Error
        
        try:
            connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                connect_timeout=10
            )
            
            if connection.is_connected():
                _logger.info(f"Successfully connected to CS-Cart database: {self.database}")
                connection.close()
                return True
                
        except Error as e:
            _logger.error(f"CS-Cart connection error: {str(e)}")
            raise
        except Exception as e:
            _logger.error(f"Unexpected connection error: {str(e)}")
            raise
    
    def _detect_cs_cart_version(self):
        """Auto-detect CS-Cart version"""
        import mysql.connector
        from mysql.connector import Error
        
        try:
            connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password
            )
            
            cursor = connection.cursor(dictionary=True)
            
            # Method 1: Check settings table
            try:
                cursor.execute("SELECT value FROM cscart_settings WHERE name='version'")
                result = cursor.fetchone()
                if result:
                    version_str = result['value']
                    # Parse version string
                    if '4.0' in version_str:
                        return '4.0'
                    elif '4.3' in version_str:
                        return '4.3'
                    elif '4.5' in version_str:
                        return '4.5'
                    elif '4.6' in version_str:
                        return '4.6'
                    elif '4.7' in version_str:
                        return '4.7'
                    elif '4.8' in version_str:
                        return '4.8'
                    elif '4.9' in version_str:
                        return '4.9'
                    elif '4.10' in version_str:
                        return '4.10'
                    elif '4.11' in version_str:
                        return '4.11'
                    elif '4.12' in version_str:
                        return '4.12'
                    elif '4.13' in version_str:
                        return '4.13'
                    elif '4.14' in version_str:
                        return '4.14'
                    elif '4.15' in version_str:
                        return '4.15'
            except:
                pass
            
            # Method 2: Check for MVE tables
            try:
                cursor.execute("SHOW TABLES LIKE 'cscart_companies'")
                if cursor.fetchone():
                    cursor.execute("SHOW TABLES LIKE 'cscart_vendor_%'")
                    if cursor.fetchone():
                        return 'mve'
            except:
                pass
            
            # Method 3: Check table structure
            try:
                cursor.execute("SHOW COLUMNS FROM cscart_products LIKE 'detailed_params'")
                if cursor.fetchone():
                    return '4.10+'
            except:
                pass
            
            return '4.0'
            
        except Error as e:
            _logger.error(f"Version detection error: {str(e)}")
            return '4.0'
        finally:
            if 'connection' in locals():
                connection.close()
    
    def get_connection(self):
        """Get MySQL connection object"""
        import mysql.connector
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.username,
            password=self.password
        )