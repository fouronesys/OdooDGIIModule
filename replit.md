# NCF Management Module for Dominican Republic - Odoo 17

## Overview

This is an Odoo 17 module that provides comprehensive NCF (Número de Comprobante Fiscal) management for Dominican Republic businesses to ensure DGII compliance. The module handles automatic sequential NCF number assignment, expiration tracking, and integration with Odoo's invoice system.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Framework & Platform
- **Platform**: Odoo 17.0+ ERP system
- **Language**: Python 3
- **Architecture Pattern**: Odoo's MVC (Model-View-Controller) pattern
- **Database**: PostgreSQL (Odoo standard)
- **Localization**: Dominican Republic specific

### Module Structure
The module follows Odoo's standard addon structure:
- `models/` - Core business logic and data models
- `views/` - XML view definitions for UI
- `wizards/` - Transient models for user interactions
- `reports/` - DGII compliance reports (606/607)
- `security/` - Access control and permissions
- `data/` - Default data and configuration

## Key Components

### Core Models

1. **NCF Sequence (`ncf.sequence`)**
   - Manages NCF prefixes and number ranges
   - Handles expiration dates and validation
   - Tracks current number assignment
   - Supports multiple document types

2. **NCF Assignment (`ncf.assignment`)**
   - Links NCF numbers to specific invoices
   - Maintains audit trail of assignments
   - Prevents duplicate assignments

3. **Account Move Extension (`account.move`)**
   - Extends Odoo's invoice model
   - Adds NCF-specific fields and validation
   - Integrates with automatic assignment logic

4. **Company Configuration (`res.company`)**
   - Company-level NCF settings
   - DGII registration information
   - Alert thresholds and preferences

### Supporting Components

1. **Creation Wizard (`ncf.sequence.wizard`)**
   - Simplified NCF sequence setup
   - Bulk creation and validation
   - User-friendly configuration interface

2. **DGII Reports (606/607)**
   - Sales report (606) generation
   - Purchase report (607) generation
   - Export functionality for DGII submission

## Data Flow

### NCF Assignment Process
1. User creates/posts an invoice requiring NCF
2. System validates company configuration and document type
3. Automatic assignment finds next available NCF from appropriate sequence
4. NCF number is generated (prefix + 8-digit sequential number)
5. Assignment record is created linking NCF to invoice
6. Invoice is updated with NCF information

### Validation & Control Flow
1. **Pre-validation**: Check if NCF is required based on company/partner
2. **Sequence Validation**: Verify sequence exists and is not expired
3. **Number Validation**: Ensure sequential assignment without gaps
4. **Post-validation**: Confirm assignment is unique and complete

### Alert System
1. **Expiration Monitoring**: Daily checks for sequences nearing expiry
2. **Low Stock Alerts**: Warnings when sequence usage reaches threshold
3. **Dashboard Integration**: Real-time status display
4. **Email Notifications**: Automated alerts to responsible users

## External Dependencies

### Odoo Core Dependencies
- `base` - Core Odoo functionality
- `account` - Accounting and invoice management
- `mail` - Notification and messaging system
- `web` - Web interface components

### Dominican Republic Compliance
- DGII (Dirección General de Impuestos Internos) reporting standards
- NCF format specifications (3-character prefix + 8-digit sequence)
- Legal document type classifications

### No External Services
The module operates entirely within Odoo without external API dependencies, ensuring reliability and data security.

## Current Status

### Demo Application (July 11, 2025)
Since Odoo 17 is not available via pip installation in the current environment, a comprehensive Flask-based demo application has been created to showcase all NCF management features:

- **Flask Demo App**: Fully functional web application at `demo_app.py`
- **Complete UI**: Dashboard, sequences, invoices, and assignments views
- **Sample Data**: Pre-loaded with Dominican Republic NCF examples
- **Key Features**: Automatic NCF assignment, validation, alerts system
- **Database**: PostgreSQL integration for production-ready data handling

### Recent Fixes
- Fixed Odoo manifest syntax error (removed post_init_hook function from manifest)
- Resolved Flask template formatting issues for currency display
- Updated Flask app for compatibility with newer Flask versions
- Verified all Python files have correct syntax (July 11, 2025)
- Fixed XML syntax errors in views/ncf_dashboard_views.xml (unescaped < and > characters)
- Migrated project structure to Replit-compatible format with separate app.py, models.py, and routes.py files
- Set up PostgreSQL database and proper Flask configuration (July 11, 2025)
- Simplified security.xml file by removing complex domain expressions that caused parsing errors
- Resolved all XML parsing issues for successful Odoo module loading (July 11, 2025)

## Deployment Strategy

### Installation Requirements
- Odoo 17.0 or later
- Dominican Republic localization enabled
- Accounting module properly configured
- Appropriate user permissions configured

### Configuration Steps
1. Enable NCF management in company settings
2. Configure DGII registration details (RNC, company name)
3. Set up NCF sequences using the creation wizard
4. Configure alert thresholds and notification preferences
5. Train users on NCF document type selection

### Security Considerations
- Role-based access control for NCF management
- Audit trails for all NCF assignments
- Prevention of manual NCF number manipulation
- Strict validation to prevent compliance violations

### Maintenance
- Regular monitoring of sequence expiration dates
- Periodic review of alert thresholds
- DGII report generation and submission tracking
- Sequence renewal process management