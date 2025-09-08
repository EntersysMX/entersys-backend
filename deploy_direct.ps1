# Direct deployment script using PowerShell SSH
# This script connects directly to the server and deploys the API

$SERVER_HOST = "34.134.14.202"
$SERVER_USER = "ajcortest"
$PROJECT_PATH = "/srv/servicios/entersys-apis/content-management"

Write-Host "🚀 Desplegando API directamente en el servidor..." -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green

Write-Host "`n1. 📥 Actualizando código desde GitHub..." -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "cd $PROJECT_PATH && git pull origin main"

Write-Host "`n2. 🐳 Reconstruyendo contenedor Docker..." -ForegroundColor Yellow  
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "cd $PROJECT_PATH && docker compose down"
Start-Sleep -Seconds 3
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "cd $PROJECT_PATH && docker compose up -d --build"

Write-Host "`n3. ⏱️ Esperando que el contenedor inicie..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "`n4. 📊 Verificando estado de contenedores..." -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "cd $PROJECT_PATH && docker compose ps"

Write-Host "`n5. 📜 Logs recientes del API..." -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "cd $PROJECT_PATH && docker compose logs api --tail=15"

Write-Host "`n6. 🧪 Probando endpoints..." -ForegroundColor Yellow
Write-Host "Health Check Local:" -ForegroundColor Cyan
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "curl -s http://localhost:8000/api/v1/health"

Write-Host "`nHealth Check Público:" -ForegroundColor Cyan  
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "curl -s https://api.dev.entersys.mx/api/v1/health"

Write-Host "`nPosts Endpoint:" -ForegroundColor Cyan
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "curl -s https://api.dev.entersys.mx/api/v1/posts"

Write-Host "`n✅ Despliegue completado!" -ForegroundColor Green
Write-Host "`n📝 Para crear el usuario admin, ejecuta:" -ForegroundColor Yellow
Write-Host ".\create_admin.ps1" -ForegroundColor White