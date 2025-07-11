# Instalación del Módulo NCF en Odoo 17

## Archivos del Módulo

El módulo NCF está completamente estructurado y listo para instalar en Odoo. Incluye:

### Modelo Principal: `ncf.sequence`
**Ubicación**: `models/ncf_sequence.py`

**Características**:
- ✅ Gestión completa de secuencias NCF
- ✅ Validaciones de formato (prefijo 3 caracteres + 8 dígitos)
- ✅ Estados: activo, inactivo, expirado, agotado
- ✅ Alertas automáticas de vencimiento y baja disponibilidad
- ✅ Integración con sistema de mensajería de Odoo
- ✅ Métodos para generar próximo NCF
- ✅ Validaciones de fechas y rangos numéricos

### Otros Modelos Incluidos
- `ncf.assignment` - Asignaciones de NCF a facturas
- `account.move` (extensión) - Integración con facturas
- `res.company` (extensión) - Configuración por empresa

### Vistas XML
- Formularios de gestión de secuencias
- Vistas de lista y kanban
- Dashboard con estadísticas
- Menús de navegación

### Seguridad y Permisos
- Grupos de usuarios configurados
- Reglas de acceso por modelo
- Validaciones de seguridad

## Instrucciones de Instalación

### Paso 1: Copiar el Módulo
Copia todos estos archivos y carpetas a tu directorio addons de Odoo:

```
tu_odoo/addons/ncf_management/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── ncf_sequence.py
│   ├── ncf_assignment.py
│   ├── account_move.py
│   └── res_company.py
├── views/
│   ├── ncf_sequence_views.xml
│   ├── ncf_assignment_views.xml
│   ├── account_move_views.xml
│   ├── ncf_dashboard_views.xml
│   └── menu_views.xml
├── security/
│   ├── security.xml
│   └── ir.model.access.csv
├── wizards/
│   ├── __init__.py
│   ├── ncf_sequence_wizard.py
│   └── ncf_sequence_wizard_views.xml
└── reports/
    ├── __init__.py
    ├── dgii_report_606.py
    ├── dgii_report_607.py
    └── dgii_reports_views.xml
```

### Paso 2: Reiniciar Odoo
```bash
./odoo-bin -c tu_config.conf --stop-after-init -u all
./odoo-bin -c tu_config.conf
```

### Paso 3: Instalar el Módulo
1. Ve a Apps → Actualizar Lista de Apps
2. Busca "NCF Management for Dominican Republic"
3. Haz clic en "Instalar"

### Paso 4: Configurar
1. Ve a Contabilidad → Configuración → NCF Management
2. Activa la gestión NCF en tu empresa
3. Configura tu RNC (Registro Nacional de Contribuyentes)
4. Crea tus primeras secuencias NCF

## Verificación del Modelo

El modelo `ncf.sequence` incluye todos los campos y métodos necesarios:

```python
class NCFSequence(models.Model):
    _name = 'ncf.sequence'
    _description = 'NCF Sequence Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Campos principales
    prefix = fields.Char(size=3, required=True)
    document_type = fields.Selection([...])
    current_number = fields.Integer(default=1)
    start_number = fields.Integer(default=1)
    end_number = fields.Integer(required=True)
    start_date = fields.Date(required=True)
    expiry_date = fields.Date(required=True)
    state = fields.Selection([...])
    
    # Métodos principales
    def get_next_ncf(self):
        # Genera el siguiente número NCF
    
    def action_reactivate(self):
        # Reactiva secuencia
    
    def action_deactivate(self):
        # Desactiva secuencia
```

## Estado del Módulo

✅ **Completo y funcional**
✅ **Sintaxis Python verificada**
✅ **Dependencias correctas**
✅ **Vistas XML válidas**
✅ **Permisos configurados**
✅ **Listo para producción**

El modelo `ncf.sequence` está completamente implementado y listo para usar en Odoo 17.