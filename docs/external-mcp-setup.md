# 外部 MCP 集成 — 运维与 P0 Spike 记录

> 设计文档：`docs/superpowers/specs/2026-06-30-external-mcp-integration-design.md`  
> 实现计划：`docs/superpowers/plans/2026-06-30-external-mcp-integration.md`

---

## P0 验收（2026-06-29）

- [x] HTTP 网关方案选定并可复现（Python FastMCP sidecar）
- [x] 从 **ai 容器内** fetch-mcp `list_tools` + `call_tool` 成功
- [x] ECS 内存决策：**C**（仅 Fetch sidecar）
- [x] test_mcp_url_guard.py 通过
- [x] MCP Client：**官方 SDK Streamable HTTP**

---


| # | 项 | 状态 | 说明 |
|---|-----|------|------|
| 1 | HTTP 网关方案 | ✅ | 自研 Python FastMCP sidecar（复用 `english-server` 镜像），放弃 Node `supergateway`（Docker Hub 拉取超时） |
| 2 | Fetch sidecar 联通 | ✅ | 本地 `uv` + Compose 内 `ai` 容器 `list_tools` → `fetch_url`；`call_tool` 抓取 `https://example.com/` 成功 |
| 3 | ECS 内存评估 | ✅ | **方案 C** — 仅 Fetch sidecar（见 §P0-2） |
| 4 | SSRF URL guard | ✅ | `server/ai/services/mcp_url_guard.py` + `scripts/test_mcp_url_guard.py` |
| 5 | MCP Client 结论 | ✅ | 官方 `mcp` SDK Streamable HTTP（方案 A） |

---

## §P0-1 — HTTP 网关方案对比

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| 社区 supergateway + `@modelcontextprotocol/server-fetch` | 官方 Fetch 实现 | 需 Node 镜像；国内 Docker Hub 超时 | ❌ 放弃 |
| 自研 Python FastMCP + httpx（与 `english_mcp` 同栈） | 复用现有镜像与依赖；可控 SSRF | 需维护 fetch 逻辑 | ✅ **选用** |
| 单容器多 stdio 子进程 gateway | 省内存 | 复杂度高 | 备选（内存不足时见 §P0-2 方案 B） |

### 实现

- 代码：`server/external_mcp/fetch_server.py`、`fetch_http_server.py`
- Compose 服务：`fetch-mcp`（内网 only，**不映射 host 端口**）
- 端点：`http://fetch-mcp:8080/mcp`
- 工具：`fetch_url(url)` — 白名单 + DNS 校验后 httpx 抓取

### 本地 spike 命令

```powershell
# 终端 1：启动 sidecar
cd server
uv run python -m external_mcp.fetch_http_server

# 终端 2：list_tools
uv run python scripts/spike_mcp_list_tools.py http://127.0.0.1:8080/mcp
# Expected: fetch_url

# call_tool 冒烟
uv run python -c "
import asyncio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
async def main():
    async with streamable_http_client('http://127.0.0.1:8080/mcp') as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            out = await s.call_tool('fetch_url', {'url': 'https://example.com/'})
            print(out.content[0].text[:120])
asyncio.run(main())
"
```

### Compose 内（从 `ai` 容器验证，勿在宿主机解析 `fetch-mcp` DNS）

```powershell
# 本地 spike 镜像（daocloud Python base）
docker build -f docker/server/Dockerfile `
  --build-arg BASE_IMAGE=docker.m.daocloud.io/library/python:3.12-slim-bookworm `
  -t local/dev/english-server:p0-spike .

$env:ACR_REGISTRY="local"; $env:ACR_NAMESPACE="dev"; $env:IMAGE_TAG="p0-spike"
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d fetch-mcp
docker compose -f deploy/docker-compose.yml --env-file deploy/.env run --rm --no-deps ai `
  uv run python scripts/spike_mcp_list_tools.py http://fetch-mcp:8080/mcp
# Expected: fetch_url
```

**2026-06-29 本地实测：** 上述命令通过。

---

## §P0-2 — ECS 内存评估

**目标主机：** `101.37.235.230`（`/opt/english-project`）

### 测量步骤

```bash
ssh root@101.37.235.230
cd /opt/english-project
free -h
docker stats --no-stream
# 部署 fetch-mcp 后再次测量
docker compose up -d fetch-mcp
docker stats --no-stream
```

### 记录（2026-06-29 ECS 实测）

| 场景 | 总内存 | ai | fetch-mcp | 其他服务合计 |
|------|--------|-----|-----------|--------------|
| 当前生产栈（无 sidecar） | **3.4Gi**（可用 **2.0Gi**） | 226.5MiB / 1.5GiB | — | nginx 17 + mcp 184 + app 241 + postgres 195 + minio 117 ≈ **754MiB** |
| + fetch-mcp（本地参考） | — | — | **145MiB / 256MiB** | 全栈 idle 约 **1.1GiB**（仍余 ~2Gi 可用） |

### 书面结论：**C — 仅 Fetch 一个 sidecar，Wikipedia/YouTube 延后**

理由：
- ECS 总内存 3.4Gi，当前六容器 idle 约 1.0Gi，余量充足但不足以舒适地跑三 sidecar（+768M limit）与后续峰值
- 单 `fetch-mcp` 实测 ~145MiB，对总栈影响约 +0.15GiB
- P1 只部署 `fetch-mcp`；Wikipedia/YouTube 模板 seed 保留但 `globally_enabled=false`，P2/P3 再启用

> 若后续升配至 ≥4Gi 且需三模板全开，可再评估方案 A 或 B。

---

## §P0-3 — SSRF URL Guard

- 模块：`server/ai/services/mcp_url_guard.py`
- 测试：`uv run python scripts/test_mcp_url_guard.py` → `OK`
- 规则：http/https、域名后缀白名单、DNS A/AAAA 解析后拦截 loopback / RFC1918 / link-local / metadata / IPv6 ULA

---

## §MCP Client（P1 采用）

**结论：方案 A — 官方 `mcp` SDK Streamable HTTP**

```python
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

async with streamable_http_client(url) as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool(name, arguments)
```

- P0 spike 脚本：`server/scripts/spike_mcp_list_tools.py`
- P1 正式化：`server/ai/services/mcp_client.py`（计划 Task 1.5）
- **不采用** 裸 `httpx` JSON-RPC（方案 B）：SDK 已处理 session 生命周期与协议细节

---

## Compose 片段（fetch-mcp）

```yaml
  fetch-mcp:
    image: ${ACR_REGISTRY}/english-project/english-server:${IMAGE_TAG}
    environment:
      FETCH_MCP_HOST: "0.0.0.0"
      FETCH_MCP_PORT: "8080"
    command: ["uv", "run", "python", "-m", "external_mcp.fetch_http_server"]
    deploy:
      resources:
        limits:
          memory: 256M
```

`ai` 服务 `depends_on: fetch-mcp`；**不**经 nginx 暴露。
