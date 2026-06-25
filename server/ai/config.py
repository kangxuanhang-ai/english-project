from pydantic_settings import BaseSettings
from pydantic import Field


class AISettings(BaseSettings):
    deepseek_api_key: str = Field(alias="DEEPSEEK_API_KEY")
    deepseek_api_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_API_MODEL")
    deepseek_reasoner_api_model: str = Field(
        default="deepseek-reasoner", alias="DEEPSEEK_REASONER_API_MODEL"
    )
    ai_database_url: str = Field(alias="AI_DATABASE_URL")
    bocha_search_url: str = Field(alias="BOCHA_SEARCH_URL")
    bocha_api_key: str = Field(alias="BOCHA_API_KEY")
    email_host: str = Field(alias="EMAIL_HOST")
    email_port: int = Field(alias="EMAIL_PORT")
    email_use_ssl: bool = Field(default=False, alias="EMAIL_USE_SSL")
    email_user: str = Field(alias="EMAIL_USER")
    email_password: str = Field(alias="EMAIL_PASSWORD")
    email_from: str = Field(alias="EMAIL_FROM")

    # 可选：推荐缓存 Redis（多 worker 部署时使用）
    redis_url: str = Field(default="", alias="REDIS_URL")
    # 可选：SlowAPI 存储，如 redis://localhost:6379
    rate_limit_storage_uri: str = Field(default="memory://", alias="RATE_LIMIT_STORAGE_URI")

    deepseek_embedding_model: str = Field(default="deepseek-embed", alias="DEEPSEEK_EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")
    knowledge_min_score: float = Field(default=0.5, alias="KNOWLEDGE_MIN_SCORE")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


ai_settings = AISettings()
