from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient

from app.config import settings


def _to_pem(raw: str, key_type: str = "RSA PRIVATE KEY") -> str:
    """将原始 base64 密钥转为 PEM 格式"""
    raw = raw.strip()
    if raw.startswith("-----"):
        return raw
    lines = [raw[i : i + 64] for i in range(0, len(raw), 64)]
    return f"-----BEGIN {key_type}-----\n" + "\n".join(lines) + f"\n-----END {key_type}-----\n"


def _to_pkcs1(raw: str) -> str:
    """PKCS#8 → PKCS#1（alipay-sdk-python 的 rsa 库需要 PKCS#1 格式）"""
    pem = _to_pem(raw, "PRIVATE KEY")
    if "RSA PRIVATE KEY" in pem:
        return pem
    try:
        from cryptography.hazmat.primitives.serialization import (
            load_pem_private_key,
            Encoding,
            PrivateFormat,
            NoEncryption,
        )

        key = load_pem_private_key(pem.encode(), password=None)
        return key.private_bytes(
            Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()
        ).decode()
    except Exception:
        return pem


class AlipayClient:
    """支付宝客户端封装（延迟初始化）"""

    def __init__(self):
        self._client: DefaultAlipayClient | None = None

    def _ensure_client(self) -> DefaultAlipayClient:
        if self._client is None:
            config = AlipayClientConfig()
            config.server_url = settings.alipay_gateway
            config.app_id = settings.alipay_app_id
            config.app_private_key = _to_pkcs1(settings.alipay_private_key)
            config.alipay_public_key = _to_pem(settings.alipay_public_key, "PUBLIC KEY")
            self._client = DefaultAlipayClient(alipay_client_config=config)
        return self._client

    def get_client(self) -> DefaultAlipayClient:
        return self._ensure_client()


alipay_client = AlipayClient()
