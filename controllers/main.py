# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json

class CsCartMigrationController(http.Controller):
    
    @http.route('/cs_cart_migration/get_progress', type='json', auth='user')
    def get_migration_progress(self, wizard_id):
        """Get migration progress via AJAX"""
        wizard = request.env['cs.cart.migration.wizard'].browse(wizard_id)
        if not wizard.exists():
            return {'error': 'Wizard not found'}
        
        return {
            'progress': wizard.progress,
            'state': wizard.state,
            'current_operation': wizard.current_operation or '',
            'log_message': wizard.log_message or '',
            'categories_imported': wizard.categories_imported,
            'products_imported': wizard.products_imported,
            'customers_imported': wizard.customers_imported,
            'suppliers_imported': wizard.suppliers_imported,
        }
    
    @http.route('/cs_cart_migration/test_connection', type='json', auth='user')
    def test_connection_api(self, host, port, database, username, password):
        """Test connection via API"""
        import mysql.connector
        from mysql.connector import Error
        
        try:
            connection = mysql.connector.connect(
                host=host,
                port=int(port),
                database=database,
                user=username,
                password=password,
                connect_timeout=5
            )
            
            if connection.is_connected():
                # Check for CS-Cart tables
                cursor = connection.cursor()
                cursor.execute("SHOW TABLES LIKE 'cscart_%'")
                tables = cursor.fetchall()
                
                cursor.close()
                connection.close()
                
                return {
                    'success': True,
                    'message': f'Connection successful! Found {len(tables)} CS-Cart tables.',
                    'table_count': len(tables),
                }
                
        except Error as e:
            return {
                'success': False,
                'message': f'Connection failed: {str(e)}',
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
            }
    
    @http.route('/cs_cart_migration/export_logs', type='http', auth='user')
    def export_migration_logs(self, connection_id=None, format='csv'):
        """Export migration logs"""
        domain = []
        if connection_id:
            domain.append(('connection_id', '=', int(connection_id)))
        
        logs = request.env['cs.cart.migration.log'].search(domain, order='create_date desc')
        
        if format == 'csv':
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Date', 'Migration Type', 'Status', 'Total Records',
                'Successful', 'Failed', 'Duration (s)', 'Error Message'
            ])
            
            # Write data
            for log in logs:
                writer.writerow([
                    log.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                    dict(log._fields['migration_type'].selection).get(log.migration_type),
                    dict(log._fields['status'].selection).get(log.status),
                    log.total_records,
                    log.successful_records,
                    log.failed_records,
                    log.duration,
                    log.error_message or '',
                ])
            
            content = output.getvalue()
            output.close()
            
            return request.make_response(content, [
                ('Content-Type', 'text/csv'),
                ('Content-Disposition', 'attachment; filename="cs_cart_migration_logs.csv"'),
            ])
        
        return request.not_found()