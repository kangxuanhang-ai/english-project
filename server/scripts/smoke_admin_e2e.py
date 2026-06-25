#!/usr/bin/env python3
"""B 端 + 知识库 RAG 端到端冒烟（Task 3.4）"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.database import async_session
from app.models.course import Course
from app.models.knowledge import DocumentStatus, KnowledgeDocument
from app.models.user import User

_API_PORT = os.environ.get("SMOKE_API_PORT", "3000")
_AI_PORT = os.environ.get("SMOKE_AI_PORT", "3001")
API = f"http://127.0.0.1:{_API_PORT}/api/v1"
AI = f"http://127.0.0.1:{_AI_PORT}/ai/v1"

ADMIN_PHONE = "13800000000"
ADMIN_PASSWORD = "admin123"
NORMAL_PHONE = "13900000099"
NORMAL_PASSWORD = "user1234"

MARKER = "SMOKE_TEST_MARKER_XYZ789"
TEST_MD = f"""# Smoke Test Document

Platform rule: students must check in daily to maintain study streak.
The English learning platform supports CET-4 and CET-6 courses.
Unique phrase: {MARKER}
"""


def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


@dataclass
class SmokeReport:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def ok(self, name: str, detail: str = "") -> None:
        msg = f"PASS  {name}" + (f" — {detail}" if detail else "")
        print(msg)
        self.passed.append(name)

    def fail(self, name: str, detail: str) -> None:
        msg = f"FAIL  {name} — {detail}"
        print(msg)
        self.failed.append(name)

    def skip(self, name: str, detail: str) -> None:
        msg = f"SKIP  {name} — {detail}"
        print(msg)
        self.skipped.append(name)

    def summary(self) -> int:
        print("\n" + "=" * 60)
        print(f"通过: {len(self.passed)}  失败: {len(self.failed)}  跳过: {len(self.skipped)}")
        if self.failed:
            print("失败项:", ", ".join(self.failed))
        return 0 if not self.failed else 1


def unwrap(resp: httpx.Response) -> dict:
    resp.raise_for_status()
    body = resp.json()
    if not body.get("success", True) and body.get("code", 200) >= 400:
        raise RuntimeError(body.get("message") or body)
    return body.get("data", body)


def login(client: httpx.Client, phone: str, password: str) -> dict:
    r = client.post(f"{API}/user/login", json={"phone": phone, "password": md5(password)})
    if r.status_code != 200:
        raise RuntimeError(f"login {phone} -> {r.status_code} {r.text[:200]}")
    data = r.json()["data"]
    token = data.get("token") or {}
    data["accessToken"] = token.get("accessToken") or data.get("accessToken")
    return data


def ensure_normal_user(client: httpx.Client) -> dict:
    r = client.post(
        f"{API}/user/register",
        json={
            "name": "SmokeUser",
            "phone": NORMAL_PHONE,
            "password": md5(NORMAL_PASSWORD),
        },
    )
    if r.status_code == 200:
        data = r.json()["data"]
        token = data.get("token") or {}
        data["accessToken"] = token.get("accessToken")
        return data
    return login(client, NORMAL_PHONE, NORMAL_PASSWORD)


def parse_sse_tools(raw: str) -> list[str]:
    tools: list[str] = []
    for line in raw.splitlines():
        if not line.startswith("data: "):
            continue
        try:
            payload = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "tool":
            tools.append(payload.get("tool", ""))
    return tools


def chat_stream(client: httpx.Client, token: str, conversation_id: str, content: str) -> str:
    with client.stream(
        "POST",
        f"{AI}/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "content": content,
            "role": "normal",
            "conversationId": conversation_id,
            "deepThink": False,
            "webSearch": False,
        },
        timeout=120.0,
    ) as resp:
        if resp.status_code != 200:
            return resp.read().decode(errors="replace")
        chunks: list[str] = []
        for line in resp.iter_lines():
            if line:
                chunks.append(line)
        return "\n".join(chunks)


async def verify_dashboard_counts(client: httpx.Client, admin_token: str) -> tuple[bool, str]:
    r = client.get(
        f"{API}/admin/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    if r.status_code != 200:
        return False, f"dashboard HTTP {r.status_code}"
    dash = r.json()["data"]

    async with async_session() as db:
        user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
        course_count = (await db.execute(select(func.count(Course.id)))).scalar() or 0
        kdoc = (await db.execute(select(func.count(KnowledgeDocument.id)))).scalar() or 0
        kready = (
            await db.execute(
                select(func.count(KnowledgeDocument.id)).where(
                    KnowledgeDocument.status == DocumentStatus.READY.value
                )
            )
        ).scalar() or 0

    mismatches = []
    if dash.get("userCount") != user_count:
        mismatches.append(f"userCount api={dash.get('userCount')} db={user_count}")
    if dash.get("courseCount") != course_count:
        mismatches.append(f"courseCount api={dash.get('courseCount')} db={course_count}")
    if dash.get("knowledgeDocCount") != kdoc:
        mismatches.append(f"knowledgeDocCount api={dash.get('knowledgeDocCount')} db={kdoc}")
    if dash.get("knowledgeReadyCount") != kready:
        mismatches.append(f"knowledgeReadyCount api={dash.get('knowledgeReadyCount')} db={kready}")

    if mismatches:
        return False, "; ".join(mismatches)
    return True, f"user={user_count} course={course_count} kdoc={kdoc}/{kready}"


def _port_listener_pids(port: int) -> list[int]:
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return []
    pids: set[int] = set()
    suffix = f":{port}"
    for line in out.splitlines():
        if "LISTENING" not in line or suffix not in line:
            continue
        parts = line.split()
        if parts and parts[-1].isdigit():
            pids.add(int(parts[-1]))
    return sorted(pids)


def check_port_health(report: SmokeReport) -> None:
    pids = _port_listener_pids(int(_API_PORT))
    if len(pids) > 1:
        report.fail(
            f"端口 {_API_PORT} 有多个监听进程",
            f"PIDs={pids}。请 taskkill /F /PID <pid> 或重启电脑后再 pnpm server",
        )
    elif len(pids) == 1:
        report.ok(f"端口 {_API_PORT} 监听", f"PID={pids[0]}")
    else:
        report.fail(f"端口 {_API_PORT} 无服务", "请先 pnpm server")


def main() -> int:
    print(f"API={API}  AI={AI}")
    print("提示: 若 3000 端口有僵尸进程，可 set SMOKE_API_PORT=3010 并改用 --port 3010 启动 server")
    print("=" * 60)
    import asyncio

    report = SmokeReport()
    client = httpx.Client(timeout=60.0)

    check_port_health(report)

    # 0. 服务健康
    try:
        h = client.get(f"http://127.0.0.1:{_API_PORT}/health")
        if h.status_code != 200:
            report.fail("服务可达", f"main API health {h.status_code}")
            return report.summary()
        report.ok("主 API 健康", h.status_code)
    except Exception as e:
        report.fail("服务可达", f"main API 不可达: {e}")
        return report.summary()

    try:
        r = client.get(f"{AI}/chat/conversations", params={"role": "normal"})
        # 未授权也证明 AI 进程在监听
        if r.status_code in (401, 403, 422):
            report.ok("AI 服务可达", f"status={r.status_code}")
        elif r.status_code == 200:
            report.ok("AI 服务可达")
        else:
            report.fail("AI 服务可达", f"status {r.status_code}")
    except Exception as e:
        report.fail("AI 服务可达", str(e))

    report.ok("Embedding 配置", f"mode={settings.embedding_mode} dims={settings.embedding_dimensions}")

    # 1. 管理员登录
    try:
        admin = login(client, ADMIN_PHONE, ADMIN_PASSWORD)
        admin_token = admin["accessToken"]
        if admin.get("role") != "admin":
            report.fail("管理员登录", f"role={admin.get('role')}")
        else:
            report.ok("管理员登录", f"role={admin['role']}")
    except Exception as e:
        report.fail("管理员登录", str(e))
        return report.summary()

    # 2. 普通用户登录 + 403
    try:
        normal = ensure_normal_user(client)
        normal_token = normal["accessToken"]
        if normal.get("role") == "admin":
            report.fail("普通用户非 admin", f"role={normal.get('role')}")
        else:
            report.ok("普通用户登录", f"role={normal.get('role', 'user')}")

        r = client.get(
            f"{API}/admin/ping",
            headers={"Authorization": f"Bearer {normal_token}"},
        )
        if r.status_code == 403:
            report.ok("非 admin 访问 admin API → 403")
        else:
            report.fail("非 admin 访问 admin API → 403", f"got {r.status_code}")
    except Exception as e:
        report.fail("普通用户鉴权", str(e))
        normal_token = None

    # 3. admin ping
    try:
        r = client.get(
            f"{API}/admin/ping",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        if r.status_code == 200 and r.json().get("data", {}).get("ok"):
            report.ok("管理员 admin/ping")
        else:
            report.fail("管理员 admin/ping", r.text[:200])
    except Exception as e:
        report.fail("管理员 admin/ping", str(e))

    # 4. 上传知识库文档
    doc_id = None
    try:
        files = {"file": ("smoke-test.md", TEST_MD.encode("utf-8"), "text/markdown")}
        r = client.post(
            f"{API}/admin/knowledge/upload",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            data={"title": "Smoke Test Doc"},
        )
        if r.status_code != 200:
            report.fail("上传 test.md", f"{r.status_code} {r.text[:300]}")
        else:
            doc_id = r.json()["data"]["id"]
            report.ok("上传 test.md", f"id={doc_id} status={r.json()['data']['status']}")
    except Exception as e:
        report.fail("上传 test.md", str(e))

    # 5. 轮询至 ready
    if doc_id:
        deadline = time.time() + 180
        final_status = "unknown"
        error_msg = ""
        while time.time() < deadline:
            r = client.get(
                f"{API}/admin/knowledge/{doc_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            doc = r.json()["data"]
            final_status = doc["status"]
            error_msg = doc.get("errorMessage") or ""
            if final_status == "ready":
                report.ok("文档 ingestion → ready", f"chunks={doc.get('chunkCount')}")
                break
            if final_status == "failed":
                report.fail("文档 ingestion → ready", error_msg or "failed")
                break
            time.sleep(3)
        else:
            report.fail("文档 ingestion → ready", f"timeout last={final_status} {error_msg}")

    # 6. 检索测试
    if doc_id and final_status == "ready":
        try:
            r = client.get(
                f"{API}/admin/knowledge/search",
                headers={"Authorization": f"Bearer {admin_token}"},
                params={"q": "students must check in daily", "topK": 5},
            )
            results = r.json()["data"]["results"]
            if not results:
                report.fail("检索测试 score ≥ 0.5", "无结果")
            else:
                top = results[0]
                score = top.get("score", 0)
                if score >= 0.5:
                    report.ok("检索测试 score ≥ 0.5", f"score={score}")
                else:
                    report.fail("检索测试 score ≥ 0.5", f"score={score}")
        except Exception as e:
            report.fail("检索测试", str(e))

    # 7. 仪表盘与 DB 一致
    try:
        ok, detail = asyncio.run(verify_dashboard_counts(client, admin_token))
        if ok:
            report.ok("仪表盘数字与 DB 一致", detail)
        else:
            report.fail("仪表盘数字与 DB 一致", detail)
    except Exception as e:
        report.fail("仪表盘数字与 DB 一致", str(e))

    # 8. 课程下架 C 端不可见
    restored_course_id = None
    try:
        r = client.get(
            f"{API}/admin/courses",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"page": 1, "pageSize": 50},
        )
        courses = r.json()["data"]["list"]
        target = next((c for c in courses if c.get("isPublished")), None)
        if not target:
            report.skip("课程下架 C 端不可见", "无已上架课程可测")
        else:
            cid = target["id"]
            client.put(
                f"{API}/admin/courses/{cid}/unpublish",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            pub = client.get(f"{API}/course/list", params={"page": 1, "pageSize": 100})
            pub_ids = {c["id"] for c in pub.json()["data"]["list"]}
            if cid in pub_ids:
                report.fail("课程下架 C 端不可见", f"course {cid} 仍在 list")
            else:
                report.ok("课程下架 C 端不可见", f"course={cid}")
            client.put(
                f"{API}/admin/courses/{cid}/publish",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            restored_course_id = cid
    except Exception as e:
        report.fail("课程下架 C 端不可见", str(e))
        if restored_course_id:
            try:
                client.put(
                    f"{API}/admin/courses/{restored_course_id}/publish",
                    headers={"Authorization": f"Bearer {admin_token}"},
                )
            except Exception:
                pass

    # 9. C 端 AI — knowledge_search & word_lookup（需 AI + DeepSeek）
    if normal_token:
        try:
            r = client.post(
                f"{AI}/chat/conversations",
                headers={"Authorization": f"Bearer {normal_token}"},
                json={"role": "normal"},
            )
            if r.status_code != 200:
                report.skip("C 端 knowledge_search", f"创建对话失败 {r.status_code}")
            else:
                conv_id = r.json()["data"]["id"]

                # 知识库问题
                stream = chat_stream(
                    client,
                    normal_token,
                    conv_id,
                    f"根据平台知识库，学生为什么要每天打卡？文档里有 {MARKER} 相关内容。",
                )
                tools = parse_sse_tools(stream)
                if "knowledge_search" in tools:
                    report.ok("C 端触发 knowledge_search", str(tools))
                else:
                    report.fail("C 端触发 knowledge_search", f"tools={tools or 'none'}")

                # 查词
                conv2 = client.post(
                    f"{AI}/chat/conversations",
                    headers={"Authorization": f"Bearer {normal_token}"},
                    json={"role": "normal"},
                ).json()["data"]["id"]
                stream2 = chat_stream(
                    client,
                    normal_token,
                    conv2,
                    "请帮我查一下单词 hello 的意思和用法。",
                )
                tools2 = parse_sse_tools(stream2)
                if "word_lookup" in tools2:
                    report.ok("C 端触发 word_lookup", str(tools2))
                else:
                    report.fail("C 端触发 word_lookup", f"tools={tools2 or 'none'}")
        except Exception as e:
            report.skip("C 端 AI 工具", str(e))

    client.close()
    return report.summary()


if __name__ == "__main__":
    raise SystemExit(main())
