# Claude Code 接入 English MCP

## 1. 获取 API Key

1. 登录 English 平台 Web
2. 打开 **设置 → MCP 连接**
3. 点击 **生成新 Key**，复制 **Key** 或 **Claude 配置**（Key 仅显示一次）

## 2. 配置 Claude Code

在 `~/.claude.json`（user scope）添加：

```json
{
  "mcpServers": {
    "english": {
      "type": "http",
      "url": "https://你的域名/mcp",
      "headers": {
        "ENGLISH-MCP-API-KEY": "en_mcp_live_你的Key"
      },
      "timeout": 60000
    }
  }
}
```

与 LangSmith 相同：Key 放在 `headers` 里，不是单独字段。

## 3. 验证

```text
/mcp          → english connected
lookup_words  → 无需 Key
get_learning_progress → 需要 Key
```

## 4. 本地开发者（stdio）

Clone 仓库后使用 `.mcp.json.example` 的 stdio 配置；`server/.env` 可配 `ENGLISH_MCP_DEMO_USER_ID`。

```powershell
cd server
uv run python -m english_mcp
```

## 5. 服务端

生产需常驻 MCP HTTP 进程：

```powershell
cd server
uv run python -m english_mcp.http_server
```

Nginx 见 `docs/deploy/nginx.example.conf` 的 `/mcp` location。

环境变量：

| 变量 | 说明 |
|------|------|
| `MCP_PUBLIC_URL` | 主 API：设置页生成的 Claude 配置 URL |
| `MCP_HTTP_HOST` / `MCP_HTTP_PORT` | MCP 监听地址 |
| `MCP_GRAMMAR_REQUIRE_KEY` | `true` 时语法检查也必须带 Key |
