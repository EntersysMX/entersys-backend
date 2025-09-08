# Setup SSH automation for Claude Code
Write-Host "🔧 Configurando automatización SSH para Claude..." -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

# Variables
$SSH_DIR = "$env:USERPROFILE\.ssh"
$KEY_PATH = "$SSH_DIR\claude_key"
$SERVER = "ajcortest@34.134.14.202"

# Crear directorio SSH si no existe
Write-Host "`n1. 📁 Creando directorio SSH..." -ForegroundColor Yellow
New-Item -Type Directory -Path $SSH_DIR -Force | Out-Null

# Generar clave SSH
Write-Host "`n2. 🔑 Generando clave SSH para automatización..." -ForegroundColor Yellow
if (-not (Test-Path $KEY_PATH)) {
    ssh-keygen -t rsa -b 4096 -C "claude-automation@entersys" -f $KEY_PATH -N ""
    Write-Host "✅ Clave generada exitosamente" -ForegroundColor Green
} else {
    Write-Host "✅ Clave ya existe" -ForegroundColor Green
}

# Mostrar clave pública
Write-Host "`n3. 📋 COPIA esta clave pública:" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Get-Content "$KEY_PATH.pub"
Write-Host "================================" -ForegroundColor Cyan

Write-Host "`n4. 🖥️ EJECUTA en el servidor:" -ForegroundColor Yellow
Write-Host "ssh ajcortest@34.134.14.202" -ForegroundColor White
Write-Host "mkdir -p ~/.ssh && chmod 700 ~/.ssh" -ForegroundColor White
Write-Host 'echo "TU_CLAVE_PUBLICA_AQUI" >> ~/.ssh/authorized_keys' -ForegroundColor White
Write-Host "chmod 600 ~/.ssh/authorized_keys" -ForegroundColor White
Write-Host "exit" -ForegroundColor White

# Probar conexión
Write-Host "`n5. 🧪 Para probar después de configurar:" -ForegroundColor Magenta
Write-Host "ssh -i $KEY_PATH -o StrictHostKeyChecking=no $SERVER 'echo Conexion exitosa'" -ForegroundColor White

Write-Host "`n6. 🔐 CLAVE PRIVADA para Claude:" -ForegroundColor Red
Write-Host "================================" -ForegroundColor Red
Get-Content $KEY_PATH
Write-Host "================================" -ForegroundColor Red

Write-Host "`n✅ Configuración completada!" -ForegroundColor Green
Write-Host "📝 Comparte la CLAVE PRIVADA con Claude para habilitar automatización" -ForegroundColor Yellow