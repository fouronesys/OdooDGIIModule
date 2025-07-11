#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar la sintaxis del módulo NCF antes de instalarlo en Odoo
"""

import ast
import os
import sys

def check_python_syntax(file_path):
    """Verifica la sintaxis de un archivo Python"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Compilar el código para verificar sintaxis
        ast.parse(content)
        print(f"✓ {file_path} - Sintaxis correcta")
        return True
    except SyntaxError as e:
        print(f"✗ {file_path} - Error de sintaxis: {e}")
        return False
    except Exception as e:
        print(f"✗ {file_path} - Error: {e}")
        return False

def check_manifest():
    """Verifica el archivo manifest"""
    manifest_path = '__manifest__.py'
    if not os.path.exists(manifest_path):
        print("✗ No se encuentra __manifest__.py")
        return False
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Evaluar el manifest como diccionario Python
        manifest = eval(content)
        
        required_keys = ['name', 'version', 'depends', 'data']
        for key in required_keys:
            if key not in manifest:
                print(f"✗ Falta clave requerida en manifest: {key}")
                return False
        
        print("✓ __manifest__.py - Estructura correcta")
        print(f"  - Nombre: {manifest['name']}")
        print(f"  - Versión: {manifest['version']}")
        print(f"  - Dependencias: {manifest['depends']}")
        
        return True
    except Exception as e:
        print(f"✗ Error en __manifest__.py: {e}")
        return False

def main():
    print("=== Verificación del Módulo NCF para Odoo ===\n")
    
    # Verificar manifest
    if not check_manifest():
        return False
    
    print()
    
    # Verificar archivos Python
    python_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                python_files.append(os.path.join(root, file))
    
    print("Verificando archivos Python:")
    all_good = True
    for py_file in sorted(python_files):
        if not check_python_syntax(py_file):
            all_good = False
    
    print()
    
    if all_good:
        print("🎉 ¡Módulo listo para instalar en Odoo!")
        print("\nPasos para instalar:")
        print("1. Copia toda la carpeta del módulo a tu directorio addons de Odoo")
        print("2. Reinicia el servidor Odoo")
        print("3. Actualiza la lista de módulos")
        print("4. Busca 'NCF Management' e instálalo")
    else:
        print("❌ Hay errores que deben corregirse antes de instalar")
    
    return all_good

if __name__ == '__main__':
    main()