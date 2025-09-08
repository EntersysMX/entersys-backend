# Create admin user script using PowerShell SSH
$SERVER_HOST = "34.134.14.202"
$SERVER_USER = "ajcortest"
$PROJECT_PATH = "/srv/servicios/entersys-apis/content-management"

Write-Host "👤 Creando usuario administrador..." -ForegroundColor Green

$createUserCommand = @"
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

ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_HOST "cd $PROJECT_PATH && $createUserCommand"

Write-Host "`n✅ Proceso completado!" -ForegroundColor Green