# English Learning Platform

Vue 3 前端 + Python FastAPI 双后端（主 API / AI 服务）的英语学习平台 monorepo。

## 仓库结构

```
english/
├── apps/web/          # @en/web — Vue 3 前端
├── apps/tracker/      # @en/tracker — 客户端埋点 SDK
├── packages/common/   # @en/common — 共享 TypeScript 类型
├── packages/config/   # @en/config — 端口常量
├── server/            # Python 后端（uv 管理，独立虚拟环境）
└── docs/              # 设计文档、部署示例、QA 记录
```

## 快速开始（开发）

### 依赖

- Node.js 20+、pnpm 9+
- Python 3.12+、[uv](https://docs.astral.sh/uv/)
- PostgreSQL（`english` + `langchain` 两个库）
- MinIO（头像存储，开发可用 Docker）

### 安装

```bash
# 前端 workspace
pnpm install

# Python 后端
cd server && uv sync
```

### 环境变量

```bash
cp server/.env.example server/.env
cp apps/web/.env.example apps/web/.env.development
```

编辑 `server/.env`：至少配置 `DATABASE_URL`、`SECRET_KEY`、`MINIO_*`、`DEEPSEEK_API_KEY`、`AI_DATABASE_URL`。  
支付宝、邮件可按需配置（支付/注册验证码功能依赖它们）。

### 数据库

```bash
cd server
uv run alembic upgrade head
uv run python seed.py
```

词库默认使用 `server/data/ecdict.sample.csv`；完整词库可设置 `ECDICT_CSV_PATH` 指向 `ecdict.csv`。

### 启动

在仓库根目录：

```bash
pnpm all    # web :8080 + API :3000 + AI :3001
# 或分别启动
pnpm web
pnpm server
pnpm ai
```

访问 http://localhost:8080

## 生产部署概要

详细步骤见 [AGENTS.md](./AGENTS.md#生产部署) 与 [docs/deploy/nginx.example.conf](./docs/deploy/nginx.example.conf)。

1. **构建前端**：`pnpm --filter @en/web build` → 静态文件在 `apps/web/dist/`
2. **后端**：在 `server/` 用 uvicorn 启动两个进程（或 systemd/supervisor）：
   - `uv run python -m uvicorn app.main:socket_app --host 0.0.0.0 --port 3000`
   - `uv run python -m uvicorn ai.main:ai_app --host 0.0.0.0 --port 3001`
3. **Nginx**：反代 `/api` → 3000、`/ai` → 3001（SSE 需关闭缓冲）、`/socket.io` → 3000；SPA `try_files`
4. **健康检查**：`GET http://<api-host>/health` 返回 `{"status":"ok","database":"up"}`
5. **环境**：生产务必更换 `SECRET_KEY`；可选 `REDIS_URL` / `RATE_LIMIT_STORAGE_URI` 用于多 worker 限流与推荐缓存

## 上线前 QA

见 [docs/qa/2026-06-25-launch-readiness-qa.md](./docs/qa/2026-06-25-launch-readiness-qa.md)。

## 文档

- [CLAUDE.md](./CLAUDE.md) / [AGENTS.md](./AGENTS.md) — 架构与命令速查
- [docs/superpowers/specs/2026-06-25-launch-readiness-full-fix-design.md](./docs/superpowers/specs/2026-06-25-launch-readiness-full-fix-design.md) — 上线修复设计
- [docs/superpowers/plans/2026-06-25-launch-readiness-full-fix-plan.md](./docs/superpowers/plans/2026-06-25-launch-readiness-full-fix-plan.md) — 实施计划
