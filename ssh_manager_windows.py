#!/usr/bin/env python3
"""
SSH Manager for Windows - Uses native SSH without sshpass
Alternative for Windows users without chocolatey/sshpass
"""

import subprocess
import sys
import os
import getpass
from pathlib import Path

class WindowsSSHManager:
    def __init__(self):
        self.server_host = "34.134.14.202"
        self.server_user = "ajcortest" 
        self.project_path = "/srv/servicios/entersys-apis/content-management"
    
    def execute_remote(self, command, interactive=False):
        """Ejecuta un comando en el servidor remoto usando SSH nativo de Windows"""
        
        if interactive:
            ssh_command = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                f"{self.server_user}@{self.server_host}"
            ]
        else:
            ssh_command = [
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
            print("❌ Error: SSH no está disponible.")
            print("   Habilítalo en Windows: Apps > Optional Features > OpenSSH Client")
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
            "docker compose logs api --tail=10"
        ]
        
        for cmd in commands:
            print(f"\n⏳ Ejecutando: {cmd}")
            success, stdout, stderr = self.execute_remote(cmd)
            if not success and "curl" not in cmd:
                print(f"❌ Falló el comando: {cmd}")
                if stderr:
                    print(f"Error detallado: {stderr}")
                return False
        
        print("\n✅ Despliegue completado")
        return True
    
    def test_api(self):
        """Prueba todos los endpoints de la API"""
        print("🧪 Probando endpoints de la API...")
        
        tests = [
            ("Health Check Local", "curl -s http://localhost:8000/api/v1/health"),
            ("Health Check Público", "curl -s https://api.dev.entersys.mx/api/v1/health"),
            ("Root Endpoint", "curl -s https://api.dev.entersys.mx/api/"),
            ("Posts Endpoint", "curl -s https://api.dev.entersys.mx/api/v1/posts"),
        ]
        
        results = []
        for name, cmd in tests:
            success, stdout, stderr = self.execute_remote(cmd)
            status = "✅" if success and stdout.strip() else "❌"
            results.append((name, status, stdout[:200]))
            print(f"{status} {name}")
        
        return results
    
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
        print(stdout)
        return success

def main():
    ssh = WindowsSSHManager()
    
    if len(sys.argv) < 2:
        print("🔧 SSH Manager para Windows (sin sshpass)")
        print("========================================")
        print("Uso:")
        print("  python ssh_manager_windows.py deploy     # Desplegar API")
        print("  python ssh_manager_windows.py test       # Probar endpoints")
        print("  python ssh_manager_windows.py user       # Crear usuario admin")
        print("  python ssh_manager_windows.py cmd 'comando'  # Ejecutar comando")
        print("  python ssh_manager_windows.py shell      # Shell interactivo")
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