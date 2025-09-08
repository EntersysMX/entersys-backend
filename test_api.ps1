# Test API endpoints script using PowerShell SSH
$SERVER_HOST = "34.134.14.202"
$SERVER_USER = "ajcortest"
$PROJECT_PATH = "/srv/servicios/entersys-apis/content-management"

Write-Host "🧪 Probando todos los endpoints de la API..." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

Write-Host "`n1. 🏥 Health Check Local:" -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "curl -s http://localhost:8000/api/v1/health"

Write-Host "`n2. 🌐 Health Check Público:" -ForegroundColor Yellow  
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "curl -s https://api.dev.entersys.mx/api/v1/health"

Write-Host "`n3. 🏠 Root Endpoint:" -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "curl -s https://api.dev.entersys.mx/api/"

Write-Host "`n4. 📝 Posts Endpoint:" -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "curl -s https://api.dev.entersys.mx/api/v1/posts"

Write-Host "`n5. 🔑 Auth Endpoint (test sin credenciales):" -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "curl -s -X POST https://api.dev.entersys.mx/api/v1/auth/token -H 'Content-Type: application/x-www-form-urlencoded' -d 'username=test&password=test'"

Write-Host "`n6. 📊 Estado de contenedores:" -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "cd $PROJECT_PATH && docker compose ps"

Write-Host "`n✅ Pruebas completadas!" -ForegroundColor Green