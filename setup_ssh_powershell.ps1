# Setup SSH access for Claude Code - PowerShell version
Write-Host "Configurando acceso SSH para Claude Code..." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

# Variables del servidor
$SERVER_HOST = "34.134.14.202"
$SERVER_USER = "ajcortest"
$PROJECT_PATH = "/srv/servicios/entersys-apis/content-management"

Write-Host "`nCreando funciones PowerShell para SSH..." -ForegroundColor Yellow

# Crear script de conexión
@"
# SSH Connection Functions for Dev Server
`$SERVER_HOST = "$SERVER_HOST"
`$SERVER_USER = "$SERVER_USER"
`$PROJECT_PATH = "$PROJECT_PATH"

function Connect-DevServer {
    `$password = Read-Host "Contraseña SSH" -AsSecureString
    `$plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR(`$password))
    
    if (`$args.Count -eq 0) {
        # Conexión interactiva
        sshpass -p "`$plainPassword" ssh -o StrictHostKeyChecking=no `$SERVER_USER@`$SERVER_HOST
    } else {
        # Ejecutar comando
        `$command = `$args -join " "
        sshpass -p "`$plainPassword" ssh -o StrictHostKeyChecking=no `$SERVER_USER@`$SERVER_HOST "cd `$PROJECT_PATH && `$command"
    }
}

function Deploy-API {
    Write-Host "🚀 Desplegando API..." -ForegroundColor Green
    Connect-DevServer "git pull origin main && docker compose up -d --build && docker compose logs api --tail=10"
}

function Test-API {
    Write-Host "🧪 Probando API..." -ForegroundColor Green
    Connect-DevServer "curl -s https://api.dev.entersys.mx/api/v1/health"
}

function Create-AdminUser {
    Write-Host "👤 Creando usuario admin..." -ForegroundColor Green
    `$createUserCommand = @"
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
"@
    Connect-DevServer `$createUserCommand
}

Write-Host "✅ Funciones disponibles:" -ForegroundColor Green
Write-Host "- Connect-DevServer 'comando'  # Ejecutar comando remoto" -ForegroundColor Cyan
Write-Host "- Deploy-API                   # Desplegar automáticamente" -ForegroundColor Cyan
Write-Host "- Test-API                     # Probar endpoints" -ForegroundColor Cyan
Write-Host "- Create-AdminUser             # Crear usuario admin" -ForegroundColor Cyan
"@ | Out-File -FilePath "ssh_functions.ps1" -Encoding UTF8

Write-Host "`n===========================================" -ForegroundColor Green
Write-Host "✅ Configuración completada!" -ForegroundColor Green
Write-Host "`nPara usar:" -ForegroundColor Yellow
Write-Host "1. Instalar sshpass: choco install sshpass" -ForegroundColor White
Write-Host "2. Cargar funciones: . .\ssh_functions.ps1" -ForegroundColor White
Write-Host "3. Usar: Deploy-API" -ForegroundColor White

# Verificar si sshpass está instalado
try {
    sshpass -V | Out-Null
    Write-Host "`n✅ sshpass ya está instalado" -ForegroundColor Green
} catch {
    Write-Host "`n⚠️ Necesitas instalar sshpass:" -ForegroundColor Yellow
    Write-Host "choco install sshpass" -ForegroundColor White
}