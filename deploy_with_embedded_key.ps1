# Automated deployment script - executes all deployment steps
Write-Host "🚀 Iniciando despliegue automático de la API..." -ForegroundColor Green

# Variables
$KEY_PATH = "C:\Web_Entersys\entersys-backend\Keyssh"
$SERVER = "ajcortest@34.134.14.202" 
$PROJECT = "/srv/servicios/entersys-apis/content-management"

Write-Host "`n1. 📥 Actualizando código desde GitHub..." -ForegroundColor Yellow
ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "cd $PROJECT; git pull origin main"

Write-Host "`n2. 🐳 Reconstruyendo contenedores..." -ForegroundColor Yellow  
ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "cd $PROJECT; docker compose down; docker compose up -d --build"

Write-Host "`n3. ⏱️ Esperando inicio de servicios..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "`n4. 🧪 Probando health check local..." -ForegroundColor Yellow
ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "curl -s http://localhost:8000/api/v1/health"

Write-Host "`n5. 🌐 Probando health check público..." -ForegroundColor Yellow  
ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "curl -s https://api.dev.entersys.mx/api/v1/health"

Write-Host "`n6. 📝 Probando endpoint de posts..." -ForegroundColor Yellow
ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "curl -s https://api.dev.entersys.mx/api/v1/posts"

Write-Host "`n7. 👤 Creando usuario administrador..." -ForegroundColor Yellow
$createUserScript = @'
docker compose exec -T api python -c "
from app.db.session import SessionLocal
from app.crud.crud_user import create_user, get_user_by_email
db = SessionLocal()
try:
    existing = get_user_by_email(db, 'admin@entersys.mx')
    if not existing:
        user = create_user(db, 'admin@entersys.mx', 'admin123')
        print(f'✅ Usuario admin creado: {user.email}')
    else:
        print(f'✅ Usuario admin ya existe: {existing.email}')
finally:
    db.close()
"
'@

ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "cd $PROJECT; $createUserScript"

Write-Host "`n8. 🔑 Probando autenticación JWT..." -ForegroundColor Yellow
ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "curl -s -X POST https://api.dev.entersys.mx/api/v1/auth/token -H `"Content-Type: application/x-www-form-urlencoded`" -d `"username=admin@entersys.mx&password=admin123`""

Write-Host "`n✅ ¡Despliegue automático completado!" -ForegroundColor Green
Write-Host "`n📋 Resumen:" -ForegroundColor Cyan
Write-Host "   - API desplegada con correcciones de importación circular" -ForegroundColor White
Write-Host "   - Usuario admin: admin@entersys.mx / admin123" -ForegroundColor White  
Write-Host "   - Endpoints disponibles:" -ForegroundColor White
Write-Host "     * GET  https://api.dev.entersys.mx/api/v1/health" -ForegroundColor Gray
Write-Host "     * POST https://api.dev.entersys.mx/api/v1/auth/token" -ForegroundColor Gray
Write-Host "     * GET  https://api.dev.entersys.mx/api/v1/posts" -ForegroundColor Gray