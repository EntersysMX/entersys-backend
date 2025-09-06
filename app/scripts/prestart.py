# app/scripts/prestart.py (Versión Final y Robusta)
import logging
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_tries = 60
wait_seconds = 2

# Imprimimos la URI que estamos intentando usar para depuración
db_uri_censored = str(settings.DATABASE_URI).replace(settings.POSTGRES_PASSWORD, "******")
logger.info(f"Esperando a la base de datos en: {db_uri_censored}")

for i in range(1, max_tries + 1):
    try:
        engine = create_engine(str(settings.DATABASE_URI))
        with engine.connect() as connection:
            logger.info("✅ ¡Conexión a la base de datos establecida exitosamente!")
            exit(0)
    except SQLAlchemyError as e:
        logger.warning(f"Intento {i}/{max_tries}: Base de datos no está lista. Reintentando...")
        logger.debug(f"Error de conexión: {e}") # Log de depuración
        time.sleep(wait_seconds)

logger.error("❌ No se pudo conectar a la base de datos después de varios intentos. Saliendo.")
exit(1)
