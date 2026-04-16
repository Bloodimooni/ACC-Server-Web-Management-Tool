from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str
    SERVER_DIR: Path = Path(r"C:\ACCServer\server")
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    HTTPS_ENABLED: bool = False
    USERS_FILE: Path = Path("users.json")

    OIDC_ENABLED: bool = False
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_DISCOVERY_URL: str = ""
    OIDC_REDIRECT_URI: str = "http://localhost:8080/auth/oidc/callback"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
