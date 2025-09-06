#!/bin/bash
# DEBUG-HEALTH.sh
# Diagnóstico específico del health endpoint

echo "🔍 DIAGNÓSTICO ESPECÍFICO DEL HEALTH ENDPOINT"
echo "============================================"

cd /srv/servicios/entersys-apis/content-management

echo "• Logs recientes del contenedor:"
echo "================================"
docker logs entersys-content-api --tail 50

echo ""
echo "• Variables de entorno en el contenedor:"
echo "======================================="
docker exec entersys-content-api env | grep -E "(POSTGRES|DATABASE|PYTHONPATH)" || echo "Sin variables relevantes"

echo ""
echo "• Test directo del código de health check desde dentro del contenedor:"
echo "==================================================================="
docker exec entersys-content-api python << 'PYTHONCODE'
import os
import sys
print("🔧 Ejecutando health check manualmente...")

# Añadir el directorio app al path
sys.path.insert(0, '/app')

try:
    print("1. Importando módulos...")
    from sqlalchemy.orm import Session
    from sqlalchemy import text
    from app.db.session import SessionLocal
    print("   ✅ Módulos importados correctamente")
    
    print("2. Creando sesión de base de datos...")
    db = SessionLocal()
    print("   ✅ Sesión creada")
    
    print("3. Ejecutando consulta SELECT 1...")
    result = db.execute(text("SELECT 1"))
    print(f"   ✅ Consulta exitosa: {result.fetchone()}")
    
    print("4. Cerrando sesión...")
    db.close()
    print("   ✅ Sesión cerrada")
    
    print("🎉 Health check manual EXITOSO")
    
except Exception as e:
    print(f"❌ Error en health check manual: {e}")
    import traceback
    traceback.print_exc()
PYTHONCODE

echo ""
echo "• Test de importación específica del endpoint de health:"
echo "======================================================"
docker exec entersys-content-api python << 'PYTHONCODE'
import sys
sys.path.insert(0, '/app')

try:
    print("Importando health endpoint...")
    from app.api.v1.endpoints.health import check_health, get_db
    print("✅ Health endpoint importado correctamente")
    
    print("Probando función get_db...")
    db_gen = get_db()
    db = next(db_gen)
    print("✅ Generador de DB funciona")
    
    # Simular el health check
    print("Ejecutando check_health...")
    from sqlalchemy import text
    db.execute(text("SELECT 1"))
    print("✅ Health check simulado funciona")
    
    db.close()
    
except Exception as e:
    print(f"❌ Error importando/ejecutando health: {e}")
    import traceback
    traceback.print_exc()
PYTHONCODE

echo ""
echo "• Test directo del endpoint HTTP:"
echo "==============================="
docker exec entersys-content-api python << 'PYTHONCODE'
import urllib.request
import urllib.error
import json

try:
    print("Haciendo request a health endpoint...")
    request = urllib.request.Request('http://localhost:8000/api/v1/health')
    request.add_header('Content-Type', 'application/json')
    
    try:
        response = urllib.request.urlopen(request, timeout=10)
        data = response.read().decode('utf-8')
        print(f"✅ Status: {response.getcode()}")
        print(f"✅ Response: {data}")
    except urllib.error.HTTPError as e:
        error_data = e.read().decode('utf-8')
        print(f"❌ HTTP Error {e.code}")
        print(f"❌ Error response: {error_data}")
        
        # Intentar parsear el JSON del error
        try:
            error_json = json.loads(error_data)
            print("📋 Error detallado:", error_json)
        except:
            print("📋 Error no es JSON válido")
            
except Exception as e:
    print(f"❌ Error general: {e}")
PYTHONCODE

echo ""
echo "• Verificando estructura de archivos de la aplicación:"
echo "===================================================="
docker exec entersys-content-api find /app -name "*.py" | head -10

echo ""
echo "• Test de conectividad básica de la aplicación:"
echo "=============================================="
docker exec entersys-content-api python << 'PYTHONCODE'
import urllib.request

endpoints_to_test = [
    'http://localhost:8000/',
    'http://localhost:8000/docs', 
    'http://localhost:8000/api/v1/health'
]

for endpoint in endpoints_to_test:
    try:
        response = urllib.request.urlopen(endpoint, timeout=5)
        print(f"✅ {endpoint} -> {response.getcode()}")
    except urllib.error.HTTPError as e:
        print(f"❌ {endpoint} -> HTTP {e.code}")
    except Exception as e:
        print(f"❌ {endpoint} -> {str(e)[:50]}...")
PYTHONCODE

echo ""
echo "✅ DIAGNÓSTICO HEALTH COMPLETADO"
echo ""
echo "💡 Revisar los resultados arriba para identificar el problema específico"