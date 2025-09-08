# Automated deployment script with embedded SSH key
Write-Host "🚀 Iniciando despliegue automático con clave integrada..." -ForegroundColor Green

# Variables
$SERVER = "ajcortest@34.134.14.202" 
$PROJECT = "/srv/servicios/entersys-apis/content-management"
$TEMP_KEY = "$env:TEMP\claude_deploy_key"

# Crear clave SSH temporal
Write-Host "`n📋 Creando clave SSH temporal..." -ForegroundColor Cyan
$SSH_KEY = @"
-----BEGIN OPENSSH PRIVATE KEY-----
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
-----END OPENSSH PRIVATE KEY-----
"@

# Escribir clave a archivo temporal
$SSH_KEY | Out-File -FilePath $TEMP_KEY -Encoding ASCII -NoNewline

try {
    Write-Host "`n1. 📥 Actualizando código desde GitHub..." -ForegroundColor Yellow
    ssh -i $TEMP_KEY -o StrictHostKeyChecking=no $SERVER "cd $PROJECT; git pull origin main"

    Write-Host "`n2. 🐳 Deteniendo contenedores..." -ForegroundColor Yellow
    ssh -i $TEMP_KEY -o StrictHostKeyChecking=no $SERVER "cd $PROJECT; docker compose down"

    Write-Host "`n3. 🔨 Reconstruyendo contenedores..." -ForegroundColor Yellow  
    ssh -i $TEMP_KEY -o StrictHostKeyChecking=no $SERVER "cd $PROJECT; docker compose up -d --build"

    Write-Host "`n4. ⏱️ Esperando inicio de servicios (15s)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15

    Write-Host "`n5. 🧪 Probando health check local..." -ForegroundColor Yellow
    ssh -i $TEMP_KEY -o StrictHostKeyChecking=no $SERVER "curl -s http://localhost:8000/api/v1/health"

    Write-Host "`n6. 🌐 Probando health check público..." -ForegroundColor Yellow
    ssh -i $TEMP_KEY -o StrictHostKeyChecking=no $SERVER "curl -s https://api.dev.entersys.mx/api/v1/health"

    Write-Host "`n7. 📝 Probando endpoint de posts..." -ForegroundColor Yellow
    ssh -i $TEMP_KEY -o StrictHostKeyChecking=no $SERVER "curl -s https://api.dev.entersys.mx/api/v1/posts"

    Write-Host "`n8. 👤 Creando usuario administrador..." -ForegroundColor Yellow
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

    ssh -i $TEMP_KEY -o StrictHostKeyChecking=no $SERVER "cd $PROJECT; $createUserScript"

    Write-Host "`n9. 🔑 Probando autenticación JWT..." -ForegroundColor Yellow
    ssh -i $TEMP_KEY -o StrictHostKeyChecking=no $SERVER "curl -s -X POST https://api.dev.entersys.mx/api/v1/auth/token -H 'Content-Type: application/x-www-form-urlencoded' -d 'username=admin@entersys.mx&password=admin123'"

    Write-Host "`n✅ ¡DESPLIEGUE COMPLETADO!" -ForegroundColor Green
    Write-Host "`n📋 RESUMEN:" -ForegroundColor Cyan
    Write-Host "   🔐 Usuario: admin@entersys.mx / admin123" -ForegroundColor White  
    Write-Host "   🌐 Health: https://api.dev.entersys.mx/api/v1/health" -ForegroundColor White
    Write-Host "   🔑 Auth:   https://api.dev.entersys.mx/api/v1/auth/token" -ForegroundColor White
    Write-Host "   📝 Posts:  https://api.dev.entersys.mx/api/v1/posts" -ForegroundColor White

} finally {
    # Limpiar archivo temporal de clave
    if (Test-Path $TEMP_KEY) {
        Remove-Item $TEMP_KEY -Force
        Write-Host "`n🧹 Clave temporal eliminada" -ForegroundColor Gray
    }
}