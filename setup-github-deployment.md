# 🔧 Configurar GitHub Actions para Deployment Automático

## 📋 Pasos para configurar el deployment directo

### 1. 🔑 Configurar SSH Key en GitHub Secrets

#### Generar SSH Key (en tu máquina local):
```bash
# Generar nueva SSH key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/entersys_deploy_key -N ""

# Mostrar la clave pública (copiar esto)
cat ~/.ssh/entersys_deploy_key.pub
```

#### Agregar clave pública al servidor:
```bash
# Conectar al servidor
gcloud compute ssh dev-server --zone=us-central1-c

# Agregar clave a authorized_keys
echo "TU_CLAVE_PUBLICA_AQUI" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

#### Agregar clave privada a GitHub Secrets:
```bash
# Mostrar clave privada (copiar esto para GitHub)
cat ~/.ssh/entersys_deploy_key
```

### 2. 🔐 Configurar GitHub Secrets

Ve a tu repositorio en GitHub:
1. Settings → Secrets and variables → Actions
2. Crear nuevo secret:
   - **Name**: `DEV_SERVER_SSH_KEY`
   - **Value**: [Pegar el contenido de la clave privada]

### 3. 🚀 Deployment Automático

Ahora cada push a `main` desplegará automáticamente:
- ✅ Clona el código en el servidor
- ✅ Configura la base de datos
- ✅ Construye y despliega el contenedor
- ✅ Verifica que funcione

### 4. 🎯 Deployment Manual

También puedes ejecutar deployment manual:
1. Ve a tu repositorio → Actions
2. Selecciona "Deploy to Development Server"
3. Click "Run workflow"

## 📱 Deployment Inmediato Alternativo

Si prefieres deployar inmediatamente sin SSH keys:

```bash
# 1. Conectar al servidor
gcloud compute ssh dev-server --zone=us-central1-c

# 2. Ejecutar deployment directo
curl -s https://raw.githubusercontent.com/EntersysMX/entersys-backend/main/ONE-COMMAND-DEPLOY.sh | bash
```

## 🌐 URLs después del deployment

- **Health Check**: https://api.dev.entersys.mx/content/v1/health
- **Documentación**: https://api.dev.entersys.mx/content/docs  
- **Root**: https://api.dev.entersys.mx/content/

## 🔍 Verificar Deployment

```bash
# Test rápido
curl https://api.dev.entersys.mx/content/v1/health

# Debe retornar:
{"status":"ok","database_connection":"ok"}
```

## ⚡ Deployment en 3 pasos:

### Opción 1: GitHub Actions (Recomendado)
1. Configurar SSH key
2. Push a main
3. ✅ Auto-deploy

### Opción 2: Un comando
1. `gcloud compute ssh dev-server --zone=us-central1-c`  
2. `curl -s https://raw.githubusercontent.com/EntersysMX/entersys-backend/main/ONE-COMMAND-DEPLOY.sh | bash`
3. ✅ Deployed