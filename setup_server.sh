#!/bin/bash

echo "🚀 Configurando servidor de desarrollo para Entersys API..."

# Navegar al directorio del proyecto
cd /srv/servicios/entersys-apis/content-management/

echo "📦 Actualizando dependencias..."
pip install -r requirements.txt

echo "🔐 Configurando variables de entorno..."
# Agregar SECRET_KEY al .env si no existe
if ! grep -q "SECRET_KEY" .env; then
    echo "" >> .env
    echo "# JWT Configuration" >> .env
    echo "SECRET_KEY=5f70P1VqUXX98HZkcWuW9GkeLDHs/euc07t0TDo8W6M=" >> .env
    echo "ALGORITHM=HS256" >> .env
    echo "ACCESS_TOKEN_EXPIRE_MINUTES=30" >> .env
fi

echo "🗄️ Ejecutando migraciones de base de datos..."
alembic upgrade head

echo "👤 Creando usuario administrador..."
python3 -c "
from app.db.session import SessionLocal
from app.crud.crud_user import create_user, get_user_by_email

db = SessionLocal()
try:
    # Verificar si ya existe el usuario admin
    existing_user = get_user_by_email(db, 'admin@entersys.mx')
    if not existing_user:
        user = create_user(db, 'admin@entersys.mx', 'admin123')
        print(f'✅ Usuario admin creado: {user.email}')
    else:
        print('✅ Usuario admin ya existe')
finally:
    db.close()
"

echo "🐳 Reiniciando contenedor Docker..."
docker compose up -d --build

echo "✅ ¡Configuración completada!"
echo ""
echo "📋 Credenciales de prueba:"
echo "Email: admin@entersys.mx"
echo "Password: admin123"
echo ""
echo "🌐 Endpoints disponibles:"
echo "- POST /api/v1/auth/token (Login)"
echo "- GET /api/v1/posts (Listar posts públicos)"
echo "- POST /api/v1/posts (Crear post - requiere auth)"
echo "- PUT /api/v1/posts/{id} (Actualizar post - requiere auth)"
echo "- DELETE /api/v1/posts/{id} (Eliminar post - requiere auth)"