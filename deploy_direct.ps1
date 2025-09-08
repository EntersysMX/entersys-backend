# Direct deployment script using PowerShell SSH
$SERVER_HOST = "34.134.14.202"
$SERVER_USER = "ajcortest" 
$PROJECT_PATH = "/srv/servicios/entersys-apis/content-management"

Write-Host "🚀 Desplegando API directamente..." -ForegroundColor Green

Write-Host "`n1. 📥 Actualizando código..." -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" "cd $PROJECT_PATH; git pull origin main"

Write-Host "`n2. 🐳 Deteniendo contenedor..." -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" "cd $PROJECT_PATH; docker compose down"

Write-Host "`n3. 🔨 Reconstruyendo contenedor..." -ForegroundColor Yellow  
ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" "cd $PROJECT_PATH; docker compose up -d --build"

Write-Host "`n4. ⏱️ Esperando inicio..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "`n5. 📊 Estado contenedores:" -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" "cd $PROJECT_PATH; docker compose ps"

Write-Host "`n6. 📜 Logs recientes:" -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" "cd $PROJECT_PATH; docker compose logs api --tail=10"

Write-Host "`n7. 🧪 Probando health check local:" -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" "curl -s http://localhost:8000/api/v1/health"

Write-Host "`n8. 🌐 Probando health check público:" -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" "curl -s https://api.dev.entersys.mx/api/v1/health"

Write-Host "`n✅ Despliegue completado!" -ForegroundColor Green