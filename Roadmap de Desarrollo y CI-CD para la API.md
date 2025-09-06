🚀 Roadmap: Desarrollo y Automatización (CI/CD) de la APIEste documento detalla los pasos a seguir para implementar la lógica de negocio de la API y automatizar su despliegue, siguiendo los hitos 4 y 5 del plan de acción principal.✅ Hitos Anteriores CompletadosInfraestructura Base: Desplegada y funcional.Conectividad: API y Base de Datos se comunican correctamente.Esquema de BD: Creado y gestionado por Alembic.Control de Versiones: Código fuente sincronizado con GitHub.fase 4: 💻 Avanzar con el Desarrollo de la APIEl objetivo de esta fase es implementar los endpoints críticos definidos en el documento MD070, enfocándonos en la autenticación y la gestión de posts del blog.Metodología de DesarrolloTrabajaremos siguiendo el flujo estándar de Git:Crear una nueva rama para la funcionalidad (feature/authentication, feature/blog-crud).Desarrollar en local.Hacer commit de los cambios.Hacer push de la rama a GitHub.Crear un Pull Request para fusionar los cambios a main.Desplegar manualmente en el dev-server para probar (hasta que la Fase 5 esté completa).Acción 4.1: Implementar Autenticación con JWTBasado en el requerimiento del MD070, implementaremos la autenticación para proteger los endpoints de administración.Paso 4.1.1: Añadir Dependencias de SeguridadAñade las siguientes librerías a tu archivo requirements.txt:passlib[bcrypt]
python-jose[cryptography]
Instálalas en tu entorno local: pip install -r requirements.txt.Paso 4.1.2: Crear el Módulo de SeguridadCrea un nuevo archivo app/core/security.py para manejar el hashing de contraseñas y la creación/verificación de tokens JWT.# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Any, Union

from jose import jwt
from passlib.context import CryptContext

# (Aquí iría el código para las funciones de seguridad)
Paso 4.1.3: Actualizar el Archivo de ConfiguraciónAñade los secretos y parámetros de JWT a tu archivo app/core/config.py y al .env.example.# app/core/config.py
class Settings(BaseSettings):
    # ...
    # --- JWT Settings ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
Paso 4.1.4: Crear los Schemas de PydanticCrea un nuevo archivo app/schemas/token.py para definir los modelos de datos de los tokens.Paso 4.1.5: Crear el Endpoint de AutenticaciónCrea un nuevo archivo app/api/v1/endpoints/auth.py con la lógica para el endpoint POST /api/v1/auth/token, que recibirá un email y contraseña, y devolverá un token de acceso.Acción 4.2: Implementar los Endpoints CRUD para Blog PostsAhora crearemos los endpoints para Crear, Leer, Actualizar y Eliminar (CRUD) los artículos del blog.Paso 4.2.1: Crear los Schemas de Pydantic para PostsCrea un nuevo archivo app/schemas/post.py para definir cómo se verán los datos de un post al ser creados, actualizados o leídos.Paso 4.2.2: Crear la Capa de Repositorio (CRUD)Crea un nuevo archivo app/crud/crud_post.py que contendrá las funciones que interactúan directamente con la base de datos (ej. get_post, create_post, update_post, delete_post).Paso 4.2.3: Crear los Endpoints de la API para PostsCrea un nuevo archivo app/api/v1/endpoints/posts.py.Implementa los siguientes endpoints, usando dependencias para proteger las rutas que lo requieran:GET /api/v1/posts: Listar todos los artículos publicados. (Público)GET /api/v1/posts/{slug}: Obtener un artículo por su slug. (Público)POST /api/v1/posts: Crear un nuevo artículo. (Protegido)PUT /api/v1/posts/{id}: Actualizar un artículo existente. (Protegido)DELETE /api/v1/posts/{id}: Eliminar un artículo. (Protegido)fase 5: 🤖 Automatizar el Despliegue con CI/CDEl objetivo de esta fase es crear un workflow de GitHub Actions que automatice el despliegue en el dev-server cada vez que se fusionen cambios a la rama main, tal como lo define el SCRAM-Infrastructure-Manual.md.Acción 5.1: Configurar los Secretos en GitHubNecesitamos darle a GitHub Actions las credenciales para que pueda conectarse a tu dev-server de forma segura.En tu repositorio de GitHub, ve a Settings > Secrets and variables > Actions.Crea los siguientes "Repository secrets":DEV_SERVER_HOST: 34.134.14.202DEV_SERVER_USER: ajcortestDEV_SERVER_SSH_KEY: Pega aquí el contenido de tu clave SSH privada (el archivo ~/.ssh/id_rsa, no el .pub).Acción 5.2: Crear el Workflow de GitHub ActionsEn tu repositorio local, dentro del directorio .github/workflows/, crea un nuevo archivo llamado deploy-dev.yml.Pega el siguiente contenido:# .github/workflows/deploy-dev.yml
name: Deploy to Development Server

# Se activa cada vez que hay un push a la rama 'main'
on:
  push:
    branches:
      - main

jobs:
  deploy:
    name: Deploy to Dev
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.7.0
        with:
          ssh-private-key: ${{ secrets.DEV_SERVER_SSH_KEY }}

      - name: Add SSH host
        run: |
          ssh-keyscan -H ${{ secrets.DEV_SERVER_HOST }} >> ~/.ssh/known_hosts

      - name: Deploy via SSH
        run: |
          ssh ${{ secrets.DEV_SERVER_USER }}@${{ secrets.DEV_SERVER_HOST }} '
            echo "--- Conectado al servidor de desarrollo ---"
            
            # Navegar al directorio del stack
            cd /srv/servicios/entersys-apis/content-management/
            
            echo "--- Actualizando código desde el repositorio ---"
            git pull origin main
            
            echo "--- Reconstruyendo y reiniciando el stack con Docker Compose ---"
            docker compose up -d --build
            
            echo "--- Despliegue completado ---"
          '
Acción 5.3: Probar el Flujo de CI/CDHaz un pequeño cambio en tu código local (ej. añade un comentario en app/main.py).Haz commit y push de este cambio a la rama main.Ve a la pestaña "Actions" en tu repositorio de GitHub.Verás que un nuevo "workflow" se ha iniciado. Puedes hacer clic en él para ver el progreso en tiempo real.Si todo está configurado correctamente, el workflow terminará con éxito, y habrás desplegado tu cambio en el dev-server sin haberte conectado manualmente.Has completado el ciclo de DevOps. ¡Felicidades!