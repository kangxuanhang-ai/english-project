import asyncio
import logging
from datetime import timedelta

from shared.minio_client import minio_client

logger = logging.getLogger(__name__)


def make_key(document_id: str, filename: str) -> str:
    return f"knowledge/{document_id}/{filename}"


def _client():
    return minio_client.get_client()


def _bucket():
    return minio_client.get_bucket()


async def upload_bytes(key: str, data: bytes, content_type: str) -> None:
    def _upload():
        from io import BytesIO

        client = _client()
        client.put_object(
            _bucket(),
            key,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    await asyncio.to_thread(_upload)


async def download_bytes(key: str) -> bytes:
    def _download():
        client = _client()
        response = client.get_object(_bucket(), key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    return await asyncio.to_thread(_download)


async def delete_object(key: str) -> None:
    def _delete():
        client = _client()
        client.remove_object(_bucket(), key)

    try:
        await asyncio.to_thread(_delete)
    except Exception as e:
        logger.warning("MinIO 删除失败 key=%s: %s", key, e)


async def presigned_download_url(key: str, expires: int = 900) -> str:
    def _url():
        client = _client()
        return client.presigned_get_object(_bucket(), key, expires=timedelta(seconds=expires))

    return await asyncio.to_thread(_url)
