# Phase 2 — LangSmith Hub Prompt 版本化

**日期**: 2026-06-29  
**状态**: 已实现  
**依赖**: Phase 1（`create_agent` + `ChatContext` middleware）

---

## 目标

6 个聊天角色的 system prompt 版本化到 LangSmith Hub；运行时拉取 + 本地 `prompt.py` fallback。

---

## Hub 命名

LangSmith 将 `owner/name` 中的 `/` 解析为租户分隔符，**不能**使用设计初稿的 `english/chat-normal`。

实际标识符：

| role | Hub ID |
|------|--------|
| normal | `english-chat-normal` |
| master | `english-chat-master` |
| business | `english-chat-business` |
| qilinge | `english-chat-qilinge` |
| xiaoman | `english-chat-xiaoman` |
| oral | `english-chat-oral` |

---

## 新增 / 修改文件

| 文件 | 说明 |
|------|------|
| `server/ai/services/prompt_loader.py` | `get_role_base_prompt(role)`：Hub pull + 5min 内存缓存 + fallback |
| `server/scripts/push_prompts_to_hub.py` | 首次 / 更新时将 `CHAT_MODES` 推送到 Hub |
| `server/ai/services/prompt.py` | 新增 `get_local_role_prompt()` |
| `server/ai/services/chat.py` | `base_prompt = await get_role_base_prompt(role)` |
| `server/.env.example` | Hub 说明注释 |

**未改动**：`middleware/chat_prompt.py`（仍从 `ChatContext.base_prompt` 拼接 search/progress）、`ai/routers/prompt.py`（列表 API 仍读本地 metadata）。

---

## 启用条件

- `LANGCHAIN_API_KEY` 非空 → 从 Hub 拉取（带缓存）
- 未配置或 Hub 异常 → `get_local_role_prompt(role)`，不 500

---

## 运维命令

```bash
cd server
# 首次或 prompt.py 变更后同步到 Hub
uv run python scripts/push_prompts_to_hub.py
```

在 LangSmith UI 编辑 prompt 后，最多 5 分钟（TTL）内聊天行为会更新。

---

## 验收清单

- [x] 6 个 prompt 已 push 到 Hub（有 commit 历史）
- [x] `get_role_base_prompt` 拉取内容与本地一致
- [ ] Hub 修改 prompt 后 5 分钟内聊天行为变化（手动）
- [ ] 断网 / 无效 key 时 fallback 本地（手动）

---

## 后续（Phase 3）

评测 dataset `english-agent-normal-v1` + `run_agent_eval.py`。
