from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    WEBHOOK_BASE_URL: str
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    TIMEZONE: str = "Europe/Moscow"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()