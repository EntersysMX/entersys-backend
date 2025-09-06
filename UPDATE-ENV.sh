#!/bin/bash
# UPDATE-ENV.sh
# Script rápido para actualizar .env con la contraseña correcta

echo "🔧 ACTUALIZANDO .env CON CONTRASEÑA CORRECTA"
echo "==========================================="

cd /srv/servicios/entersys-apis/content-management

echo "• .env anterior:"
cat .env

echo ""
echo "• Creando .env con contraseña correcta..."
cat > .env << 'ENVEOF'
POSTGRES_USER=entersys_user
POSTGRES_PASSWORD=Operaciones.2025
POSTGRES_SERVER=dev-entersys-postgres
POSTGRES_DB=entersys_db
POSTGRES_PORT=5432
ENVEOF

echo "• .env actualizado:"
cat .env

echo ""
echo "• Reiniciando API para cargar nueva configuración..."
docker-compose restart content-api

echo "• Esperando 20 segundos..."
sleep 20

echo "• Test rápido:"
docker exec entersys-content-api python -c "
import os
print('Variables de entorno:')
print('POSTGRES_PASSWORD:', os.getenv('POSTGRES_PASSWORD', 'NO_SET'))
print('POSTGRES_USER:', os.getenv('POSTGRES_USER', 'NO_SET'))
print('POSTGRES_SERVER:', os.getenv('POSTGRES_SERVER', 'NO_SET'))
"

echo ""
echo "✅ .env actualizado - ahora ejecuta el test manual"