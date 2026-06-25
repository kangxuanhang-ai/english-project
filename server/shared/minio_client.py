import json
import logging

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)


class MinioClient:
    """MinIO 客户端封装（延迟初始化）"""

    def __init__(self):
        self._client: Minio | None = None
        self.bucket = settings.minio_bucket

    def _ensure_client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                endpoint=f"{settings.minio_endpoint}:{settings.minio_port}",
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_use_ssl,
            )
        return self._client

    async def init_bucket(self):
        """初始化 bucket：不存在则创建并设置公共读策略"""
        client = self._ensure_client()
        try:
            if not client.bucket_exists(self.bucket):
                client.make_bucket(self.bucket)
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicReadObjects",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket}/*"],
                        }
                    ],
                }
                client.set_bucket_policy(self.bucket, json.dumps(policy))
                logger.info("MinIO bucket '%s' created with public read policy", self.bucket)
            else:
                logger.info("MinIO bucket '%s' already exists", self.bucket)
        except S3Error as e:
            logger.error("MinIO init error: %s", e)

    def get_client(self) -> Minio:
        return self._ensure_client()

    def get_bucket(self) -> str:
        return self.bucket


minio_client = MinioClient()
