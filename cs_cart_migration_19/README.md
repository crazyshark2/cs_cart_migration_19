# CS-Cart to Odoo Migration Tool

## Overview
This Odoo module facilitates the migration of data from CS-Cart e-commerce platform to Odoo 19.

## Features
- **Database Connection**: Configure connection to CS-Cart MySQL database
- **Data Migration**: Migrate products, categories, customers, orders
- **Progress Tracking**: Real-time migration progress monitoring
- **Error Handling**: Comprehensive error logging and reporting
- **Batch Processing**: Process large datasets in batches

## Installation

### Prerequisites
- Odoo 19.0
- Python 3.7+
- MySQL server with CS-Cart database

### Steps
1. Install the module in Odoo
2. Go to Apps > CS-Cart Migration
3. Configure database connection
4. Start migration wizard

## Configuration

### CS-Cart Database
1. Ensure MySQL access is enabled
2. Create a read-only user for migration
3. Whitelist Odoo server IP in MySQL

### Odoo Configuration
1. Install required Python packages:
   ```bash
   pip install -r requirements.txt
