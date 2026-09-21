from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "在线题库与刷题平台"
    VERSION: str = "1.0.0"

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "exam_platform"

    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"


settings = Settings()
