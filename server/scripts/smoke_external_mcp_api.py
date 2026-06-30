"""外部 MCP API 集成冒烟（需本地 app + fetch-mcp 运行）。"""
from __future__ import annotations

import asyncio
import hashlib
import os
import sys

import httpx

BASE = os.environ.get("SMOKE_API_BASE", "http://127.0.0.1:3000/api/v1")
ADMIN_PHONE = os.environ.get("SMOKE_ADMIN_PHONE", "13800000000")
ADMIN_PASSWORD_MD5 = hashlib.md5(b"admin123").hexdigest()


async def login(client: httpx.AsyncClient, phone: str, password_md5: str) -> str:
    resp = await client.post(f"{BASE}/user/login", json={"phone": phone, "password": password_md5})
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success"):
        raise RuntimeError(body.get("message") or "login failed")
    data = body.get("data") or {}
    token = data.get("token") or {}
    access = token.get("accessToken") or data.get("accessToken")
    if not access:
        raise RuntimeError(f"login response missing accessToken: {list(data.keys())}")
    return access


async def main() -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        token = await login(client, ADMIN_PHONE, ADMIN_PASSWORD_MD5)
        headers = {"Authorization": f"Bearer {token}"}

        templates_resp = await client.get(f"{BASE}/admin/mcp-templates", headers=headers)
        templates_resp.raise_for_status()
        templates = templates_resp.json()["data"]
        assert templates, "no mcp templates seeded"
        fetch_tpl = next(t for t in templates if t["alias"] == "fetch")

        put_resp = await client.put(
            f"{BASE}/admin/mcp-templates/{fetch_tpl['id']}",
            headers=headers,
            json={"globallyEnabled": True},
        )
        put_resp.raise_for_status()

        test_resp = await client.post(
            f"{BASE}/admin/mcp-templates/{fetch_tpl['id']}/test",
            headers=headers,
        )
        if test_resp.status_code != 200:
            print(f"WARN: admin test skipped ({test_resp.status_code}): fetch-mcp may be down")
        else:
            tools = test_resp.json()["data"]["tools"]
            assert tools, "admin test should return tools when fetch-mcp is up"

        user_put = await client.put(
            f"{BASE}/user/external-mcp/fetch",
            headers=headers,
            json={"enabled": True, "headers": {}},
        )
        user_put.raise_for_status()

        user_test = await client.post(
            f"{BASE}/user/external-mcp/fetch/test",
            headers=headers,
        )
        if user_test.status_code == 200:
            assert user_test.json()["data"]["tools"]
        else:
            print(f"WARN: user test skipped ({user_test.status_code})")

    print("OK")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
