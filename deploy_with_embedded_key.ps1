# Automated deployment script with embedded SSH key
Write-Host "🚀 Iniciando despliegue automático con clave integrada..." -ForegroundColor Green

# Variables
$SERVER = "ajcortest@34.134.14.202" 
$PROJECT = "/srv/servicios/entersys-apis/content-management"
$TEMP_KEY = "$env:TEMP\claude_deploy_key"

# Usar archivo de clave existente
Write-Host "`n📋 Usando clave SSH existente..." -ForegroundColor Cyan
$KEY_PATH = "C:\Web_Entersys\entersys-backend\Keyssh"

try {
    Write-Host "`n1. 📥 Actualizando código desde GitHub..." -ForegroundColor Yellow
    ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "cd $PROJECT; git pull origin main"

    Write-Host "`n2. 🐳 Deteniendo contenedores..." -ForegroundColor Yellow
    ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "cd $PROJECT; docker compose down"

    Write-Host "`n3. 🔨 Reconstruyendo contenedores..." -ForegroundColor Yellow  
    ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "cd $PROJECT; docker compose up -d --build"

    Write-Host "`n4. ⏱️ Esperando inicio de servicios (15s)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15

    Write-Host "`n5. 🧪 Probando health check local..." -ForegroundColor Yellow
    ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "curl -s http://localhost:8000/api/v1/health"

    Write-Host "`n6. 🌐 Probando health check público..." -ForegroundColor Yellow
    ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "curl -s https://api.dev.entersys.mx/api/v1/health"

    Write-Host "`n7. 📝 Probando endpoint de posts..." -ForegroundColor Yellow
    ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "curl -s https://api.dev.entersys.mx/api/v1/posts"

    Write-Host "`n8. 👤 Creando usuario administrador..." -ForegroundColor Yellow
    $createUserScript = 'docker compose exec -T api python -c "from app.db.session import SessionLocal; from app.crud.crud_user import create_user, get_user_by_email; db = SessionLocal(); existing = get_user_by_email(db, ''admin@entersys.mx''); user = create_user(db, ''admin@entersys.mx'', ''admin123'') if not existing else existing; print(f''Usuario: {user.email}''); db.close()"'

    ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER "cd $PROJECT; $createUserScript"

    Write-Host "`n9. 🔑 Probando autenticación JWT..." -ForegroundColor Yellow
    ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER 'curl -s -X POST https://api.dev.entersys.mx/api/v1/auth/token -H "Content-Type: application/x-www-form-urlencoded" -d "username=admin@entersys.mx&password=admin123"'

    Write-Host "`n✅ ¡DESPLIEGUE COMPLETADO!" -ForegroundColor Green
    Write-Host "`n📋 RESUMEN:" -ForegroundColor Cyan
    Write-Host "   🔐 Usuario: admin@entersys.mx / admin123" -ForegroundColor White  
    Write-Host "   🌐 Health: https://api.dev.entersys.mx/api/v1/health" -ForegroundColor White
    Write-Host "   🔑 Auth:   https://api.dev.entersys.mx/api/v1/auth/token" -ForegroundColor White
    Write-Host "   📝 Posts:  https://api.dev.entersys.mx/api/v1/posts" -ForegroundColor White

} catch {
    Write-Host "`n❌ Error durante el despliegue: $($_.Exception.Message)" -ForegroundColor Red
}