#!/bin/bash

# Script completo de prueba para la API con JWT
API_BASE="https://api.dev.entersys.mx/api"

echo "🚀 Probando API completa de Entersys con JWT..."
echo "================================================"

echo ""
echo "1. 🏥 Verificando salud de la API..."
HEALTH_CHECK=$(curl -s "$API_BASE/v1/health")
echo "Health check: $HEALTH_CHECK"

if [[ $HEALTH_CHECK == *"healthy"* ]]; then
    echo "✅ API está saludable"
else
    echo "❌ API no responde correctamente al health check"
    echo "Intentando health check en localhost..."
    curl -s "http://localhost:8000/api/v1/health" || echo "❌ Tampoco responde en localhost"
    exit 1
fi

echo ""
echo "2. 🔗 Verificando endpoint raíz..."
ROOT_RESPONSE=$(curl -s "$API_BASE/")
echo "Root response: $ROOT_RESPONSE"

echo ""
echo "3. 🔑 Intentando obtener token con credenciales de prueba..."
TOKEN_RESPONSE=$(curl -s -X POST "$API_BASE/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@entersys.mx&password=admin123")

echo "Token response: $TOKEN_RESPONSE"

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token' 2>/dev/null)

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
    echo "✅ Token obtenido exitosamente: ${TOKEN:0:30}..."
else
    echo "⚠️ No se pudo obtener token (posiblemente usuario no existe aún)"
    echo "Esto es normal en la primera ejecución"
fi

echo ""
echo "4. 📖 Probando endpoint de posts públicos..."
POSTS_RESPONSE=$(curl -s "$API_BASE/v1/posts")
echo "Posts response: $POSTS_RESPONSE"

if [[ $POSTS_RESPONSE == "["* ]]; then
    echo "✅ Endpoint de posts responde correctamente (array JSON)"
else
    echo "❌ Endpoint de posts no responde como esperado"
fi

echo ""
echo "5. 🧪 Probando endpoint específico (404 esperado)..."
SINGLE_POST=$(curl -s "$API_BASE/v1/posts/test-post")
echo "Single post response: $SINGLE_POST"

echo ""
echo "================================================"
echo "📋 Resumen de la prueba:"
echo "- Health Check: $(if [[ $HEALTH_CHECK == *"healthy"* ]]; then echo "✅ OK"; else echo "❌ FAIL"; fi)"
echo "- Root endpoint: $(if [[ -n $ROOT_RESPONSE ]]; then echo "✅ OK"; else echo "❌ FAIL"; fi)"  
echo "- Auth endpoint: $(if [[ $TOKEN_RESPONSE == *"access_token"* ]] || [[ $TOKEN_RESPONSE == *"error"* ]]; then echo "✅ OK (responde)"; else echo "❌ FAIL (no responde)"; fi)"
echo "- Posts endpoint: $(if [[ $POSTS_RESPONSE == "["* ]]; then echo "✅ OK"; else echo "❌ FAIL"; fi)"
echo ""

if [[ $HEALTH_CHECK == *"healthy"* ]] && [[ $POSTS_RESPONSE == "["* ]]; then
    echo "🎉 ¡API funcionando correctamente!"
    echo ""
    echo "📝 Para crear el usuario admin, ejecuta en el servidor:"
    echo 'docker exec -it entersys-content-api python -c "'
    echo 'from app.db.session import SessionLocal'
    echo 'from app.crud.crud_user import create_user, get_user_by_email'
    echo 'db = SessionLocal()'
    echo 'try:'
    echo '    if not get_user_by_email(db, \"admin@entersys.mx\"):'
    echo '        user = create_user(db, \"admin@entersys.mx\", \"admin123\")'
    echo '        print(f\"Usuario creado: {user.email}\")'
    echo '    else:'
    echo '        print(\"Usuario ya existe\")'
    echo 'finally:'
    echo '    db.close()'
    echo '"'
else
    echo "❌ Hay problemas con la API que requieren atención"
fi