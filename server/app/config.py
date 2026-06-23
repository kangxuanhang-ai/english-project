from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置，从 .env 文件读取"""

    # 数据库
    database_url: str = Field(alias="DATABASE_URL")

    # JWT
    secret_key: str = Field(alias="SECRET_KEY")

    # MinIO
    minio_endpoint: str = Field(alias="MINIO_ENDPOINT")
    minio_port: int = Field(default=9000, alias="MINIO_PORT")
    minio_use_ssl: bool = Field(default=False, alias="MINIO_USE_SSL")
    minio_access_key: str = Field(alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="avatar", alias="MINIO_BUCKET")

    # DeepSeek
    deepseek_api_key: str = Field(alias="DEEPSEEK_API_KEY")
    deepseek_api_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_API_MODEL")
    deepseek_reasoner_api_model: str = Field(
        default="deepseek-reasoner", alias="DEEPSEEK_REASONER_API_MODEL"
    )

    # AI 数据库
    ai_database_url: str = Field(alias="AI_DATABASE_URL")

    # Bocha 搜索
    bocha_search_url: str = Field(alias="BOCHA_SEARCH_URL")
    bocha_api_key: str = Field(alias="BOCHA_API_KEY")

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:8080"], alias="CORS_ORIGINS")

    # 支付宝
    alipay_app_id: str = Field(alias="ALIPAY_APP_ID")
    alipay_private_key: str = Field(alias="ALIPAY_PRIVATE_KEY")
    alipay_public_key: str = Field(alias="ALIPAY_PUBLIC_KEY")
    alipay_gateway: str = Field(alias="ALIPAY_GATEWAY")
    alipay_notify_url: str = Field(alias="ALIPAY_NOTIFY_URL")
    alipay_return_url: str = Field(default="http://localhost:8080/courses/index", alias="ALIPAY_RETURN_URL")

    # 邮件
    email_host: str = Field(alias="EMAIL_HOST")
    email_port: int = Field(alias="EMAIL_PORT")
    email_use_ssl: bool = Field(default=False, alias="EMAIL_USE_SSL")
    email_user: str = Field(alias="EMAIL_USER")
    email_password: str = Field(alias="EMAIL_PASSWORD")
    email_from: str = Field(alias="EMAIL_FROM")

    # ClickHouse
    clickhouse_url: str = Field(default="", alias="CLICKHOUSE_URL")
    clickhouse_username: str = Field(default="", alias="CLICKHOUSE_USERNAME")
    clickhouse_password: str = Field(default="", alias="CLICKHOUSE_PASSWORD")
    clickhouse_database: str = Field(default="", alias="CLICKHOUSE_DATABASE")

    # 端口配置
    server_port: int = 3000
    ai_port: int = 3001
    web_port: int = 8080

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
