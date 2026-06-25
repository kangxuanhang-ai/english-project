from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import logging

logger = logging.getLogger(__name__)

_WEAK_SECRET_KEYS = frozenset(
    {
        "secret",
        "change-me",
        "changeme",
        "change-me-in-production-use-openssl-rand",
    }
)


class AppSettings(BaseSettings):
    """主 API 配置（port 3000），从 .env 读取。不含 AI 专用变量。"""

    database_url: str = Field(alias="DATABASE_URL")
    secret_key: str = Field(alias="SECRET_KEY")

    minio_endpoint: str = Field(alias="MINIO_ENDPOINT")
    minio_port: int = Field(default=9000, alias="MINIO_PORT")
    minio_use_ssl: bool = Field(default=False, alias="MINIO_USE_SSL")
    minio_access_key: str = Field(alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="avatar", alias="MINIO_BUCKET")

    cors_origins: list[str] = Field(default=["http://localhost:8080"], alias="CORS_ORIGINS")

    alipay_app_id: str = Field(alias="ALIPAY_APP_ID")
    alipay_private_key: str = Field(alias="ALIPAY_PRIVATE_KEY")
    alipay_public_key: str = Field(alias="ALIPAY_PUBLIC_KEY")
    alipay_gateway: str = Field(alias="ALIPAY_GATEWAY")
    alipay_notify_url: str = Field(alias="ALIPAY_NOTIFY_URL")
    alipay_return_url: str = Field(
        default="http://localhost:8080/courses/index", alias="ALIPAY_RETURN_URL"
    )

    email_host: str = Field(alias="EMAIL_HOST")
    email_port: int = Field(alias="EMAIL_PORT")
    email_use_ssl: bool = Field(default=False, alias="EMAIL_USE_SSL")
    email_user: str = Field(alias="EMAIL_USER")
    email_password: str = Field(alias="EMAIL_PASSWORD")
    email_from: str = Field(alias="EMAIL_FROM")

    clickhouse_url: str = Field(default="", alias="CLICKHOUSE_URL")
    clickhouse_username: str = Field(default="", alias="CLICKHOUSE_USERNAME")
    clickhouse_password: str = Field(default="", alias="CLICKHOUSE_PASSWORD")
    clickhouse_database: str = Field(default="", alias="CLICKHOUSE_DATABASE")

    server_port: int = 3000
    ai_port: int = 3001
    web_port: int = 8080

    deepseek_api_key: str = Field(alias="DEEPSEEK_API_KEY")
    deepseek_embedding_model: str = Field(default="deepseek-embed", alias="DEEPSEEK_EMBEDDING_MODEL")
    embedding_mode: str = Field(default="local", alias="EMBEDDING_MODE")
    embedding_api_base: str = Field(
        default="https://api.deepseek.com/v1", alias="EMBEDDING_API_BASE"
    )
    local_embedding_model: str = Field(
        default="BAAI/bge-small-zh-v1.5", alias="LOCAL_EMBEDDING_MODEL"
    )
    embedding_dimensions: int = Field(default=512, alias="EMBEDDING_DIMENSIONS")
    knowledge_max_file_size: int = Field(default=20971520, alias="KNOWLEDGE_MAX_FILE_SIZE")
    knowledge_chunk_size: int = Field(default=500, alias="KNOWLEDGE_CHUNK_SIZE")
    knowledge_chunk_overlap: int = Field(default=50, alias="KNOWLEDGE_CHUNK_OVERLAP")
    knowledge_min_score: float = Field(default=0.5, alias="KNOWLEDGE_MIN_SCORE")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        normalized = v.strip().lower()
        if len(v) < 16 or normalized in _WEAK_SECRET_KEYS:
            logger.warning(
                "SECRET_KEY 过短或为默认值，生产环境请使用足够长的随机字符串"
            )
        return v


settings = AppSettings()
