# Docker + GitHub Actions 部署指南（阿里云 ECS）

公网访问：`http://101.37.235.230`  
C 端 `/` · B 端 admin `/admin/` · API `/api/` · AI `/ai/` · MinIO 反代 `/minio/`

合并到 `main` 分支后，GitHub Actions 自动构建镜像、推送到 GHCR，并 SSH 到 ECS 执行 `docker compose up`。

---

## 一、架构

| 容器 | 说明 |
|------|------|
| `nginx` | 80 端口，静态资源 + 反代 |
| `app` | 主 API + Socket.IO（3000） |
| `ai` | AI 聊天、推荐、邮件 digest 定时任务（3001） |
| `postgres` | `english` + `langchain` 库（pgvector） |
| `minio` | 头像、课程封面 |

---

## 二、ECS 一次性准备

### 1. 安全组

| 端口 | 用途 |
|------|------|
| 22 | SSH（建议仅允许你的 IP） |
| 80 | HTTP 网站 |

可关闭 FRP 用的 7000、18080。

### 2. 安装 Docker Compose（若 `docker compose` 不可用）

```bash
# root 登录 ECS 后
docker --version
docker compose version
```

Ubuntu 预装 Docker 时通常已包含 Compose 插件。

### 3. 生成 SSH 密钥（在你 Windows 本机 PowerShell）

```powershell
ssh-keygen -t ed25519 -C "github-actions-deploy" -f "$env:USERPROFILE\.ssh\english_deploy"
```

将公钥 `english_deploy.pub` 内容追加到 ECS：

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "粘贴公钥内容" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

本机测试：

```powershell
ssh -i $env:USERPROFILE\.ssh\english_deploy root@101.37.235.230
```

### 4. GitHub Personal Access Token（拉取私有镜像）

在 GitHub → Settings → Developer settings → Personal access tokens 创建 **classic** token，勾选：

- `read:packages`

记下 token，用于 Secret `GHCR_PULL_TOKEN`。

---

## 三、配置 GitHub Secrets

仓库 `english-project` → **Settings → Secrets and variables → Actions**：

| Secret | 说明 |
|--------|------|
| `ECS_HOST` | `101.37.235.230` |
| `ECS_USER` | `root` |
| `ECS_SSH_KEY` | 私钥 `english_deploy` 全文 |
| `GHCR_PULL_TOKEN` | 上一步 PAT（read:packages） |
| `SERVER_ENV` | 生产 `.env` 全文（见下） |

### 生成 `SERVER_ENV`

1. 复制 `deploy/env.production.example` 为草稿  
2. 填入真实密钥（可从本地 `server/.env` 迁移，并改以下项）：

```env
POSTGRES_PASSWORD=你的强密码
DATABASE_URL=postgresql://postgres:你的强密码@postgres:5432/english
AI_DATABASE_URL=postgresql://postgres:你的强密码@postgres:5432/langchain

MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=你的minio密码
MINIO_ENDPOINT=minio
MINIO_PUBLIC_BASE=http://101.37.235.230/minio

ALIPAY_NOTIFY_URL=http://101.37.235.230
ALIPAY_RETURN_URL=http://101.37.235.230/courses/index
CORS_ORIGINS=["http://101.37.235.230"]

# 邮件（单词记忆报告）
EMAIL_HOST=smtp.qq.com
EMAIL_PORT=465
EMAIL_USE_SSL=true
EMAIL_USER=你的QQ邮箱
EMAIL_PASSWORD=QQ邮箱授权码
EMAIL_FROM=你的QQ邮箱
```

3. 将整份文件内容粘贴到 Secret `SERVER_ENV`（不要提交到 Git）

---

## 四、首次部署

1. 合并部署相关代码到 `main`  
2. 打开 GitHub → Actions → **Deploy to ECS**，查看运行日志  
3. 成功后验证：

```bash
curl http://101.37.235.230/health
# {"status":"ok","database":"up"}

curl -I http://101.37.235.230/
curl -I http://101.37.235.230/admin/
```

4. 浏览器访问：
   - C 端：http://101.37.235.230  
   - Admin：http://101.37.235.230/admin/  
   - 管理员：`13800000000` / `admin123`（seed 预置）

---

## 五、支付宝沙箱

- 异步回调：`http://101.37.235.230/api/v1/pay/notify`（由 `ALIPAY_NOTIFY_URL` + 代码拼接）  
- 同步跳回：`http://101.37.235.230/courses/index`  
- 使用沙箱**买家账号**付款，可停用 Windows FRP

---

## 六、邮件测试

部署后在 ECS 上：

```bash
cd /opt/english-project
docker compose exec app uv run python scripts/test_email.py 你的邮箱@example.com
```

用户侧：设置页填写邮箱 → 开启定时任务 → 当天学习单词 → 次日收到「单词记忆报告」。

---

## 七、日常运维

```bash
cd /opt/english-project

# 查看状态
docker compose ps

# 日志
docker compose logs -f app
docker compose logs -f ai
docker compose logs -f nginx

# 手动拉取最新（一般 Actions 会自动做）
export IMAGE_TAG=<git-sha>
docker compose pull && docker compose up -d
```

---

## 八、故障排查

| 现象 | 处理 |
|------|------|
| Actions SSH 失败 | 检查 `ECS_SSH_KEY`、安全组 22、ECS `authorized_keys` |
| `pull` 401 | 检查 `GHCR_PULL_TOKEN` 是否有 read:packages |
| `/health` 503 | `docker compose logs app`，多为数据库密码与 `DATABASE_URL` 不一致 |
| 头像/封面裂图 | 确认 `MINIO_PUBLIC_BASE=http://101.37.235.230/minio` |
| AI 容器 OOM | 在 `.env` 设 `EMBEDDING_MODE=api`（需 `DEEPSEEK_API_KEY`），然后 `docker compose up -d` |
| 支付不成功 | 沙箱买家账号、`ALIPAY_NOTIFY_URL` 无端口、安全组 80 开放 |

---

## 九、本地调试 Compose（可选）

```bash
cp deploy/env.production.example deploy/.env
# 编辑 deploy/.env

docker compose -f deploy/docker-compose.yml --env-file deploy/.env build
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d
```

本地需把 `MINIO_PUBLIC_BASE`、`CORS_ORIGINS` 等改为 `http://localhost`。
