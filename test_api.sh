#!/bin/bash

API_BASE="http://34.134.14.202:8000"

echo "🧪 Probando API de Entersys..."

echo ""
echo "1. 🏥 Verificando salud de la API..."
curl -s "$API_BASE/api/v1/health" | jq '.' || echo "❌ Health check failed"

echo ""
echo "2. 🔑 Obteniendo token de autenticación..."
TOKEN=$(curl -s -X POST "$API_BASE/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@entersys.mx&password=admin123" | jq -r '.access_token')

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    echo "✅ Token obtenido: ${TOKEN:0:20}..."
else
    echo "❌ No se pudo obtener el token"
    exit 1
fi

echo ""
echo "3. 📝 Creando post de prueba..."
POST_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/posts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Mi primer post",
    "slug": "mi-primer-post",
    "content": "Este es el contenido de mi primer post de prueba",
    "status": "published",
    "meta_description": "Post de prueba para la API"
  }')

POST_ID=$(echo $POST_RESPONSE | jq -r '.id')
echo "✅ Post creado con ID: $POST_ID"

echo ""
echo "4. 📖 Obteniendo posts públicos..."
curl -s "$API_BASE/api/v1/posts" | jq '.[0] | {id, title, slug, status}' || echo "❌ No se pudieron obtener los posts"

echo ""
echo "5. 🔍 Obteniendo post por slug..."
curl -s "$API_BASE/api/v1/posts/mi-primer-post" | jq '{title, content, status}' || echo "❌ No se pudo obtener el post"

echo ""
echo "✅ ¡Todas las pruebas completadas!"