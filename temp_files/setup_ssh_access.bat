@echo off
echo Configurando acceso SSH para Claude Code...
echo ==========================================

echo.
echo Instalando sshpass usando chocolatey...
choco install sshpass -y

echo.
echo Creando script de conexion SSH...
echo @echo off > ssh_dev.bat
echo set SERVER_HOST=34.134.14.202 >> ssh_dev.bat
echo set SERVER_USER=ajcortest >> ssh_dev.bat
echo set /p SERVER_PASS="Ingresa la contraseña para %SERVER_USER%@%SERVER_HOST%: " >> ssh_dev.bat
echo sshpass -p "%%SERVER_PASS%%" ssh -o StrictHostKeyChecking=no %%SERVER_USER%%@%%SERVER_HOST%% "cd /srv/servicios/entersys-apis/content-management && %%*" >> ssh_dev.bat

echo.
echo Creando script de ejecución remota...
echo @echo off > remote_exec.bat
echo if "%%1"=="" ( >> remote_exec.bat
echo     echo Uso: remote_exec.bat "comando a ejecutar" >> remote_exec.bat
echo     exit /b 1 >> remote_exec.bat
echo ) >> remote_exec.bat
echo set SERVER_HOST=34.134.14.202 >> remote_exec.bat
echo set SERVER_USER=ajcortest >> remote_exec.bat
echo set /p SERVER_PASS="Contraseña SSH: " >> remote_exec.bat
echo sshpass -p "%%SERVER_PASS%%" ssh -o StrictHostKeyChecking=no %%SERVER_USER%%@%%SERVER_HOST%% "cd /srv/servicios/entersys-apis/content-management && %%~1" >> remote_exec.bat

echo.
echo ==========================================
echo ✅ Configuracion completada!
echo.
echo Para usar:
echo 1. remote_exec.bat "git pull origin main"
echo 2. remote_exec.bat "docker compose up -d --build"
echo 3. remote_exec.bat "./manual_deploy.sh"
echo.
echo También puedes conectarte interactivamente con:
echo ssh_dev.bat