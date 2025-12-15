# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class TestConnectionWizard(models.TransientModel):
    _name = 'cs.cart.test.connection.wizard'
    _description = 'Test CS-Cart Connection'
    
    host = fields.Char(string='Host', required=True, default='localhost')
    port = fields.Integer(string='Port', required=True, default=3306)
    database = fields.Char(string='Database Name', required=True)
    username = fields.Char(string='Username', required=True, default='root')
    password = fields.Char(string='Password', required=True)
    
    connection_status = fields.Selection([
        ('not_tested', 'Not Tested'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Connection Status', default='not_tested', readonly=True)
    
    error_message = fields.Text(string='Error Message', readonly=True)
    
    def action_test_connection(self):
        """Test the database connection"""
        self.ensure_one()
        
        try:
            import mysql.connector
            from mysql.connector import Error
            
            connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                connect_timeout=10
            )
            
            if connection.is_connected():
                # Get database info
                cursor = connection.cursor(dictionary=True)
                
                # Try to detect CS-Cart
                try:
                    cursor.execute("SHOW TABLES LIKE 'cscart_%'")
                    cs_cart_tables = cursor.fetchall()
                    
                    if cs_cart_tables:
                        # Try to get version
                        try:
                            cursor.execute("SELECT value FROM cscart_settings WHERE name='version'")
                            version_result = cursor.fetchone()
                            version_info = version_result['value'] if version_result else 'Unknown'
                        except:
                            version_info = 'Table exists but cannot read version'
                        
                        message = _('✅ Connection successful!\n')
                        message += _('CS-Cart database detected.\n')
                        message += _('Tables found: %d\n') % len(cs_cart_tables)
                        message += _('Version: %s') % version_info
                    else:
                        message = _('✅ Connection successful!\n')
                        message += _('⚠️ No CS-Cart tables found. Is this a CS-Cart database?')
                    
                except Exception as e:
                    message = _('✅ Connection successful!\n')
                    message += _('⚠️ Cannot check for CS-Cart tables: %s') % str(e)
                
                cursor.close()
                connection.close()
                
                self.write({
                    'connection_status': 'success',
                    'error_message': message,
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Connection test completed successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
                
        except Error as e:
            error_msg = _('❌ Connection failed!\n\nError: %s\n\n') % str(e)
            error_msg += _('Please check:\n')
            error_msg += _('1. Host and port are correct\n')
            error_msg += _('2. Database name is correct\n')
            error_msg += _('3. Username and password are correct\n')
            error_msg += _('4. MySQL server is running\n')
            error_msg += _('5. Remote connections are allowed (if applicable)')
            
            self.write({
                'connection_status': 'failed',
                'error_message': error_msg,
            })
            
            raise UserError(_('Connection failed: %s') % str(e))
        
        except Exception as e:
            error_msg = _('❌ Unexpected error!\n\nError: %s') % str(e)
            self.write({
                'connection_status': 'failed',
                'error_message': error_msg,
            })
            
            raise UserError(_('Connection test failed: %s') % str(e))
    
    def action_save_connection(self):
        """Save connection details to a new connection record"""
        self.ensure_one()
        
        if self.connection_status != 'success':
            raise UserError(_('Please test the connection successfully before saving'))
        
        # Create new connection record
        connection = self.env['cs.cart.connection'].create({
            'name': _('Connection to %s') % self.database,
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'password': self.password,
        })
        
        # Auto-detect version
        try:
            detected_version = connection._detect_cs_cart_version()
            if detected_version:
                connection.cs_cart_version = detected_version
        except:
            pass
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('CS-Cart Connection'),
            'res_model': 'cs.cart.connection',
            'view_mode': 'form',
            'res_id': connection.id,
            'target': 'current',
        }