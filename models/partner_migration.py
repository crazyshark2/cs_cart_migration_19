# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from .migration_base import MigrationBase

_logger = logging.getLogger(__name__)

class PartnerMigration(models.Model):
    _name = 'cs.cart.partner.migration'
    _description = 'CS-Cart Partner Migration'
    _inherit = 'cs.cart.migration.base'
    
    def migrate_customers(self, connection, batch_size=100, update_existing=True):
        """Migrate customers from CS-Cart to Odoo"""
        import mysql.connector
        from mysql.connector import Error
        
        log = self._create_migration_log(connection, 'customer')
        migrated_customers = []
        
        try:
            conn = connection.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Customer query for CS-Cart
            query = """
                SELECT u.user_id, u.email, u.firstname, u.lastname,
                       u.phone, u.fax, u.company, u.address, u.city,
                       u.state, u.country, u.zipcode, u.status,
                       u.timestamp, u.user_type
                FROM cscart_users u
                WHERE u.user_type = 'C' AND u.status = 'A'
                ORDER BY u.user_id
            """
            
            cursor.execute(query)
            customers = cursor.fetchall()
            log.total_records = len(customers)
            self._update_migration_log(log, processed_records=0)
            
            for i, cust in enumerate(customers, 1):
                try:
                    odoo_partner = self._create_or_update_customer(cust, update_existing)
                    if odoo_partner:
                        migrated_customers.append(odoo_partner.id)
                        log.successful_records += 1
                    
                    log.processed_records = i
                    
                    # Batch commit
                    if i % batch_size == 0:
                        self.env.cr.commit()
                        _logger.info(f"Processed {i} customers")
                
                except Exception as e:
                    self._handle_migration_error(log, e, cust.get('user_id', 'unknown'))
                    continue
            
            # Update connection
            connection.last_sync_date = fields.Datetime.now()
            
            # Update log
            self._update_migration_log(log, 
                status='completed' if log.failed_records == 0 else 'partial',
                details=f"Successfully migrated {len(migrated_customers)} customers"
            )
            
            _logger.info(f"Customer migration completed: {len(migrated_customers)} customers")
            
        except Error as e:
            self._update_migration_log(log, 
                status='failed',
                error_message=f"Database error: {str(e)}"
            )
            raise UserError(_('Customer migration failed: %s') % str(e))
        except Exception as e:
            self._update_migration_log(log, 
                status='failed',
                error_message=f"Unexpected error: {str(e)}"
            )
            raise UserError(_('Customer migration failed: %s') % str(e))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
        
        return migrated_customers
    
    def migrate_suppliers(self, connection, batch_size=100, update_existing=True):
        """Migrate suppliers from CS-Cart to Odoo (for Mve edition)"""
        import mysql.connector
        from mysql.connector import Error
        
        log = self._create_migration_log(connection, 'supplier')
        migrated_suppliers = []
        
        try:
            conn = connection.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Supplier query for CS-Cart Mve
            query = self._get_cs_cart_query(connection.cs_cart_version, 'suppliers')
            
            cursor.execute(query)
            suppliers = cursor.fetchall()
            log.total_records = len(suppliers)
            self._update_migration_log(log, processed_records=0)
            
            for i, sup in enumerate(suppliers, 1):
                try:
                    odoo_partner = self._create_or_update_supplier(sup, update_existing)
                    if odoo_partner:
                        migrated_suppliers.append(odoo_partner.id)
                        log.successful_records += 1
                    
                    log.processed_records = i
                    
                    # Batch commit
                    if i % batch_size == 0:
                        self.env.cr.commit()
                        _logger.info(f"Processed {i} suppliers")
                
                except Exception as e:
                    self._handle_migration_error(log, e, sup.get('user_id', 'unknown'))
                    continue
            
            # Update connection
            connection.last_sync_date = fields.Datetime.now()
            
            # Update log
            self._update_migration_log(log, 
                status='completed' if log.failed_records == 0 else 'partial',
                details=f"Successfully migrated {len(migrated_suppliers)} suppliers"
            )
            
            _logger.info(f"Supplier migration completed: {len(migrated_suppliers)} suppliers")
            
        except Error as e:
            self._update_migration_log(log, 
                status='failed',
                error_message=f"Database error: {str(e)}"
            )
            raise UserError(_('Supplier migration failed: %s') % str(e))
        except Exception as e:
            self._update_migration_log(log, 
                status='failed',
                error_message=f"Unexpected error: {str(e)}"
            )
            raise UserError(_('Supplier migration failed: %s') % str(e))
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
        
        return migrated_suppliers
    
    def _create_or_update_customer(self, cust_data, update_existing):
        """Create or update a customer in Odoo"""
        # Check if partner already exists
        existing_partner = self.env['res.partner'].search([
            ('cs_cart_id', '=', cust_data['user_id'])
        ], limit=1)
        
        # Prepare partner name
        firstname = cust_data.get('firstname', '')
        lastname = cust_data.get('lastname', '')
        company = cust_data.get('company', '')
        
        if company:
            partner_name = company
        elif firstname or lastname:
            partner_name = f"{firstname} {lastname}".strip()
        else:
            partner_name = cust_data.get('email', 'Unknown Customer')
        
        # Get country and state IDs
        country_id = self._get_country_id(cust_data.get('country'))
        state_id = self._get_state_id(cust_data.get('state'), country_id)
        
        # Prepare partner values
        partner_vals = {
            'name': partner_name,
            'email': cust_data.get('email', ''),
            'phone': cust_data.get('phone', ''),
            'mobile': cust_data.get('fax', ''),
            'street': cust_data.get('address', ''),
            'city': cust_data.get('city', ''),
            'state_id': state_id,
            'country_id': country_id,
            'zip': cust_data.get('zipcode', ''),
            'company_name': company,
            'customer_rank': 1,
            'supplier_rank': 0,
            'active': cust_data.get('status', 'A') == 'A',
            'cs_cart_id': cust_data['user_id'],
            'is_company': bool(company),
        }
        
        # Handle existing partner
        if existing_partner:
            if update_existing:
                existing_partner.write(partner_vals)
                return existing_partner
            else:
                return existing_partner
        else:
            # Create new partner
            return self.env['res.partner'].create(partner_vals)
    
    def _create_or_update_supplier(self, sup_data, update_existing):
        """Create or update a supplier in Odoo"""
        # Similar to customer but with supplier_rank = 1
        existing_partner = self.env['res.partner'].search([
            ('cs_cart_id', '=', sup_data['user_id'])
        ], limit=1)
        
        # Prepare partner values (similar to customer)
        partner_vals = {
            'name': sup_data.get('vendor_name') or sup_data.get('company') or 'Unknown Supplier',
            'email': sup_data.get('email', ''),
            'phone': sup_data.get('phone', ''),
            'customer_rank': 0,
            'supplier_rank': 1,
            'active': sup_data.get('status', 'A') == 'A',
            'cs_cart_id': sup_data['user_id'],
            'is_company': True,
        }
        
        # Handle existing partner
        if existing_partner:
            if update_existing:
                existing_partner.write(partner_vals)
                return existing_partner
            else:
                return existing_partner
        else:
            # Create new partner
            return self.env['res.partner'].create(partner_vals)
    
    def _get_country_id(self, country_code):
        """Get Odoo country ID from country code"""
        if not country_code:
            return False
        
        country = self.env['res.country'].search([
            ('code', '=', country_code.upper())
        ], limit=1)
        
        return country.id if country else False
    
    def _get_state_id(self, state_name, country_id):
        """Get Odoo state ID from state name"""
        if not state_name or not country_id:
            return False
        
        state = self.env['res.country.state'].search([
            ('name', 'ilike', state_name),
            ('country_id', '=', country_id)
        ], limit=1)
        
        return state.id if state else False