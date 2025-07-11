# NCF Management System - Dominican Republic

This project provides comprehensive NCF (Número de Comprobante Fiscal) management for Dominican Republic businesses to ensure DGII compliance.

## Project Structure

This repository contains **TWO SYSTEMS**:

### 1. Flask Demo Application (Development/Testing)
**Currently Running on Port 5000**

The Flask app is ready to use immediately:
- **URL**: http://localhost:5000
- **Features**: Full NCF management functionality
- **Database**: PostgreSQL (configured automatically)
- **Purpose**: Development, testing, and standalone deployment

**Files for Flask App:**
- `app.py` - Flask application setup
- `flask_models.py` - Database models for Flask
- `routes.py` - Web routes and business logic
- `templates/` - HTML templates
- `main.py` - Entry point

### 2. Odoo Module (Production)
**For deployment in Odoo 17 environments**

**Files for Odoo Module:**
- `__manifest__.py` - Odoo module manifest
- `models/` - Odoo model definitions
- `views/` - XML view definitions
- `security/` - Access rights and security
- `wizards/` - Odoo wizards
- `reports/` - DGII reports

## How to Use Each System

### Using the Flask Application (Ready Now)
1. The Flask app is already running on port 5000
2. Access the dashboard at: http://localhost:5000
3. Create NCF sequences, manage invoices, and assign NCF numbers
4. All features are fully functional

### Using the Odoo Module
1. **Copy only the Odoo files** to your Odoo addons directory:
   ```bash
   # Copy these files/folders to your Odoo addons directory:
   __manifest__.py
   models/
   views/
   security/
   wizards/
   reports/
   data/
   ```

2. **Do NOT copy these Flask-specific files to Odoo:**
   - `app.py`
   - `flask_models.py`
   - `routes.py`
   - `main.py`
   - `templates/`

3. Install the module in Odoo 17:
   - Go to Apps menu
   - Search for "NCF Management"
   - Click Install

## Current Status

✅ **Flask Application**: Fully functional and running
✅ **Odoo Module**: Complete and ready for installation
✅ **Database**: PostgreSQL configured
✅ **All Features**: Dashboard, sequences, invoices, assignments

## Key Features

- **NCF Sequence Management**: Create and manage fiscal number sequences
- **Automatic Assignment**: Auto-assign NCF numbers to invoices
- **Compliance Alerts**: Track expiration dates and low availability
- **DGII Reports**: Generate 606/607 compliance reports
- **Dashboard**: Real-time statistics and monitoring
- **Security**: Role-based access control and validation

## Technical Details

- **Framework**: Flask (demo) / Odoo 17 (production)
- **Database**: PostgreSQL
- **Language**: Python 3.11
- **Localization**: Dominican Republic specific
- **Compliance**: DGII standards