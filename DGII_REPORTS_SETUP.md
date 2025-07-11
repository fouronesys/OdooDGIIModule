# DGII Reports Setup Instructions

## After Installing the NCF Management Module

The core NCF management functionality is now working. To add the DGII reports menu items, follow these steps:

### Option 1: Manual Menu Creation (Recommended)

1. Go to **Settings > Technical > User Interface > Menu Items**
2. Click **Create** to add a new menu item
3. Fill in the details for Report 606:
   - **Name**: Report 606 (Sales)
   - **Parent Menu**: Search for "DGII Reports"
   - **Action**: Search for "DGII Report 606 - Sales"
   - **Sequence**: 10
4. Click **Save**
5. Repeat for Report 607:
   - **Name**: Report 607 (Purchases)
   - **Parent Menu**: Search for "DGII Reports"
   - **Action**: Search for "DGII Report 607 - Purchases"
   - **Sequence**: 20

### Option 2: XML Data Import

You can also import the following XML data directly:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_dgii_report_606" 
              name="Report 606 (Sales)" 
              parent="ncf_management.menu_dgii_reports"
              action="ncf_management.action_dgii_report_606"
              sequence="10"/>

    <menuitem id="menu_dgii_report_607" 
              name="Report 607 (Purchases)" 
              parent="ncf_management.menu_dgii_reports"
              action="ncf_management.action_dgii_report_607"
              sequence="20"/>
</odoo>
```

### Why This Setup?

The DGII report menus were separated to avoid XML loading order issues during module installation. The core NCF functionality (sequences, assignments, dashboard) works perfectly without these menus, and the reports can be accessed through the Actions menu or added manually as described above.

### Core Features Available:

- ✅ NCF Sequence Management
- ✅ NCF Assignment to Invoices
- ✅ NCF Dashboard with Statistics
- ✅ Invoice Integration
- ✅ Company Configuration
- ✅ DGII Report Generation (via Actions menu)
- ✅ NCF Sequence Wizard

The module is fully functional for all NCF management needs!