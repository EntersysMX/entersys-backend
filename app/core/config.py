# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, computed_field

class Settings(BaseSettings):
    """
    Gestiona la configuración de la aplicación cargando variables de entorno.
    Utiliza Pydantic para la validación de tipos.
    """
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_case=True, extra="ignore"
    )

    # Variables de la base de datos leídas desde el archivo .env
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    # --- JWT Settings ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # --- Mautic CRM Settings ---
    MAUTIC_BASE_URL: str
    MAUTIC_CLIENT_ID: str
    MAUTIC_CLIENT_SECRET: str

    # --- Google OAuth Settings ---
    GOOGLE_CLIENT_ID: str = "placeholder_client_id"
    GOOGLE_CLIENT_SECRET: str = "placeholder_client_secret"

    # --- Smartsheet Configuration ---
    SMARTSHEET_ACCESS_TOKEN: str
    SMARTSHEET_API_BASE_URL: str = "https://api.smartsheet.com/2.0"
    MIDDLEWARE_API_KEY: str
    SHEET_ID: int = 7060277951418244  # ID de la hoja de Smartsheet para onboarding

    # --- Email/SMTP Settings ---
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "armando.cortes@entersys.mx"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@entersys.mx"
    SMTP_FROM_NAME: str = "Entersys"
    FRONTEND_URL: str = "https://admin.entersys.mx"

    @computed_field
    @property
    def DATABASE_URI(self) -> str:
        """
        Genera la URI de conexión a la base de datos en formato SQLAlchemy.
        Pydantic validará que la URI construida sea correcta.
        """
        dsn = PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )
        return str(dsn)

# Instancia única de la configuración que será usada en toda la aplicación.
settings = Settings()
