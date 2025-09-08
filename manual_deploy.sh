#!/bin/bash

echo "🚀 Despliegue manual para entersys-backend"
echo "=========================================="

echo ""
echo "1. 📥 Actualizando código desde GitHub..."
git pull origin main

echo ""
echo "2. 📋 Verificando archivos disponibles..."
ls -la *.sh

echo ""
echo "3. 📝 Últimos commits:"
git log --oneline -3

echo ""
echo "4. 🐳 Reconstruyendo contenedor Docker..."
docker compose down
sleep 2
docker compose up -d --build

echo ""
echo "5. ⏱️ Esperando que el contenedor inicie..."
sleep 10

echo ""
echo "6. 📊 Estado de contenedores:"
docker compose ps

echo ""
echo "7. 📜 Logs recientes del API:"
docker compose logs api --tail=15

echo ""
echo "8. 🧪 Probando endpoints localmente..."
echo "Health check:"
curl -s http://localhost:8000/api/v1/health | jq '.' 2>/dev/null || curl -s http://localhost:8000/api/v1/health

echo ""
echo "Root endpoint:"
curl -s http://localhost:8000/ | jq '.' 2>/dev/null || curl -s http://localhost:8000/

echo ""
echo "Posts endpoint:"
curl -s http://localhost:8000/api/v1/posts | jq '.' 2>/dev/null || curl -s http://localhost:8000/api/v1/posts

echo ""
echo "9. 🌐 Probando endpoint público..."
echo "Public health check:"
curl -s https://api.dev.entersys.mx/api/v1/health | jq '.' 2>/dev/null || curl -s https://api.dev.entersys.mx/api/v1/health

echo ""
echo "=========================================="
echo "✅ Despliegue manual completado"
echo ""
echo "Si todos los endpoints responden correctamente,"
echo "procede a crear el usuario administrador con:"
echo ""
echo 'docker compose exec api python -c "'
echo 'from app.db.session import SessionLocal'
echo 'from app.crud.crud_user import create_user, get_user_by_email'
echo 'db = SessionLocal()'
echo 'try:'
echo '    existing = get_user_by_email(db, \"admin@entersys.mx\")'
echo '    if not existing:'
echo '        user = create_user(db, \"admin@entersys.mx\", \"admin123\")'
echo '        print(f\"✅ Usuario admin creado: {user.email}\")'
echo '    else:'
echo '        print(f\"✅ Usuario admin ya existe: {existing.email}\")'
echo 'finally:'
echo '    db.close()'
echo '"'