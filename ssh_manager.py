#!/usr/bin/env python3
"""
SSH Manager for Claude Code - Direct server access
Allows Claude to execute commands on the remote server
"""

import subprocess
import sys
import os
import getpass
from pathlib import Path

class SSHManager:
    def __init__(self):
        self.server_host = "34.134.14.202"
        self.server_user = "ajcortest"
        self.project_path = "/srv/servicios/entersys-apis/content-management"
        self.password = None
    
    def get_password(self):
        if not self.password:
            self.password = getpass.getpass(f"Contraseña SSH para {self.server_user}@{self.server_host}: ")
        return self.password
    
    def execute_remote(self, command, interactive=False):
        """Ejecuta un comando en el servidor remoto"""
        password = self.get_password()
        
        if interactive:
            ssh_command = [
                "sshpass", "-p", password,
                "ssh", "-o", "StrictHostKeyChecking=no",
                f"{self.server_user}@{self.server_host}"
            ]
        else:
            ssh_command = [
                "sshpass", "-p", password,
                "ssh", "-o", "StrictHostKeyChecking=no",
                f"{self.server_user}@{self.server_host}",
                f"cd {self.project_path} && {command}"
            ]
        
        try:
            if interactive:
                result = subprocess.run(ssh_command)
                return result.returncode == 0
            else:
                result = subprocess.run(ssh_command, capture_output=True, text=True)
                print(f"🔧 Ejecutando: {command}")
                print(f"📤 Salida: {result.stdout}")
                if result.stderr:
                    print(f"❌ Error: {result.stderr}")
                return result.returncode == 0, result.stdout, result.stderr
        except FileNotFoundError:
            print("❌ Error: sshpass no está instalado.")
            print("   Instálalo con: choco install sshpass")
            return False
    
    def deploy_api(self):
        """Despliega la API completa"""
        print("🚀 Iniciando despliegue de API...")
        
        commands = [
            "git pull origin main",
            "docker compose down",
            "docker compose up -d --build",
            "sleep 10",
            "docker compose ps",
            "curl -s http://localhost:8000/api/v1/health"
        ]
        
        for cmd in commands:
            success, stdout, stderr = self.execute_remote(cmd)
            if not success and cmd != "curl -s http://localhost:8000/api/v1/health":
                print(f"❌ Falló el comando: {cmd}")
                return False
        
        print("✅ Despliegue completado")
        return True
    
    def test_api(self):
        """Prueba todos los endpoints de la API"""
        print("🧪 Probando endpoints de la API...")
        
        tests = [
            ("Health Check", "curl -s https://api.dev.entersys.mx/api/v1/health"),
            ("Root Endpoint", "curl -s https://api.dev.entersys.mx/api/"),
            ("Posts Endpoint", "curl -s https://api.dev.entersys.mx/api/v1/posts"),
        ]
        
        for name, cmd in tests:
            success, stdout, stderr = self.execute_remote(cmd)
            print(f"{'✅' if success else '❌'} {name}: {stdout[:100]}...")
    
    def create_admin_user(self):
        """Crea el usuario administrador"""
        print("👤 Creando usuario administrador...")
        
        create_cmd = '''docker compose exec -T api python -c "
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
"'''
        
        success, stdout, stderr = self.execute_remote(create_cmd)
        return success

def main():
    ssh = SSHManager()
    
    if len(sys.argv) < 2:
        print("🔧 SSH Manager para Claude Code")
        print("=================================")
        print("Uso:")
        print("  python ssh_manager.py deploy     # Desplegar API")
        print("  python ssh_manager.py test       # Probar endpoints")
        print("  python ssh_manager.py user       # Crear usuario admin")
        print("  python ssh_manager.py cmd 'comando'  # Ejecutar comando")
        print("  python ssh_manager.py shell      # Shell interactivo")
        return
    
    action = sys.argv[1]
    
    if action == "deploy":
        ssh.deploy_api()
    elif action == "test":
        ssh.test_api()
    elif action == "user":
        ssh.create_admin_user()
    elif action == "cmd" and len(sys.argv) > 2:
        command = sys.argv[2]
        ssh.execute_remote(command)
    elif action == "shell":
        ssh.execute_remote("", interactive=True)
    else:
        print("❌ Acción no reconocida")

if __name__ == "__main__":
    main()