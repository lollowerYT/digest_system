from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Существующие поля
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    SECRET_KEY: str
    ALGORITHM: str
    BOT_TOKEN: str

    API_ID: int
    API_HASH: str
    PHONE_NUMBER: str

    REDIS_HOST: str
    REDIS_PORT: int

    OLLAMA_HOST: str
    SAIGA_MODEL: str

    AUDIO_STORAGE_PATH: str

    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"

settings = Settings()
