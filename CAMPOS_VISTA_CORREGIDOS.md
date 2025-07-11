# ✅ Campos de Vista Corregidos para Odoo 17

## Problema Resuelto

**Error Original**:
```
El campo 'ncf_assignment_id' que se usa en modifier 'invisible' (not ncf_assignment_id) debe estar presente en la vista, pero no se encuentra
```

## Causa del Problema

En Odoo 17, **todos los campos usados en condiciones `invisible`, `required`, `readonly`** deben estar presentes en la vista, aunque sean invisibles.

## Solución Aplicada

### ❌ **Antes** - Campo Faltante
```xml
<!-- El campo ncf_assignment_id no estaba definido en la vista -->
<button name="action_assign_ncf" 
        invisible="not requires_ncf or ncf_assignment_id">
<!-- ERROR: ncf_assignment_id no existe en la vista -->
```

### ✅ **Después** - Campo Agregado
```xml
<!-- Campos invisible agregados para las condiciones -->
<field name="requires_ncf" invisible="1"/>
<field name="ncf_assignment_id" invisible="1"/>

<!-- Ahora las condiciones funcionan correctamente -->
<button name="action_assign_ncf" 
        invisible="not requires_ncf or ncf_assignment_id">
```

## Campos Agregados a la Vista

En `views/account_move_views.xml`:

```xml
<xpath expr="//field[@name='journal_id']" position="after">
    <field name="requires_ncf" invisible="1"/>          <!-- Para condiciones -->
    <field name="ncf_assignment_id" invisible="1"/>     <!-- Para condiciones -->
    <field name="ncf_document_type" 
           invisible="not requires_ncf"
           required="requires_ncf and state == 'draft'"
           readonly="state != 'draft'"/>
    <field name="ncf_number" 
           invisible="not requires_ncf"/>
</xpath>
```

## Verificación de Compatibilidad

### Campos Definidos en la Vista
- ✅ `requires_ncf` (invisible="1")
- ✅ `ncf_assignment_id` (invisible="1")  
- ✅ `ncf_document_type` (visible condicional)
- ✅ `ncf_number` (visible condicional)

### Campos Usados en Condiciones
- ✅ `requires_ncf` → Presente
- ✅ `ncf_assignment_id` → Presente
- ✅ `state` → Campo nativo de Odoo

## Estado Final

✅ **Todos los campos requeridos están presentes**
✅ **Sintaxis Odoo 17 moderna**
✅ **No más errores de campos faltantes**
✅ **Módulo listo para instalación**

## Funcionamiento Esperado

1. **Botón "Assign NCF"**: Visible solo cuando la factura requiere NCF y no tiene NCF asignado
2. **Botón "View NCF"**: Visible solo cuando ya hay un NCF asignado
3. **Campo Tipo Documento**: Visible solo para facturas que requieren NCF
4. **Campo NCF Number**: Visible solo para facturas que requieren NCF

El módulo NCF está ahora completamente compatible con Odoo 17.