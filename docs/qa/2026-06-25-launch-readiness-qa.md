# 上线就绪 QA 记录（2026-06-25）

依据 [launch-readiness 设计](../superpowers/specs/2026-06-25-launch-readiness-full-fix-design.md) §6。

**执行环境**：Windows 10，本地 `server/.env` 已配置，PostgreSQL 可用。


| ID    | 场景                            | 结果       | 说明                                           |
| ----- | ----------------------------- | -------- | -------------------------------------------- |
| QA-01 | `pnpm --filter @en/web build` | **通过**   | 构建 0 error（有大 chunk 体积警告，非阻塞）                |
| QA-02 | 新 DB migrate + seed           | **部分通过** | `seed.py` 可运行；全新空库需再跑 `alembic upgrade head` |
| QA-03 | 注册→登录→refresh→/chat           | **待人工**  | 浏览器：注册验证码 → 登录 → 聊天发消息                       |
| QA-04 | 推荐 1/3、再推荐、刷新、切对话             | **待人工**  | normal 角色；卡片与文案一致，无 JSON 泄漏                  |
| QA-05 | 支付沙箱全流程                       | **待人工**  | 支付宝沙箱 + 公网 notify；Socket payload 正常          |
| QA-06 | 词库学习后推荐变化                     | **待人工**  | 掌握单词后 sync；再推荐应有变化                           |
| QA-07 | 口语：语音+TTS+grammar             | **待人工**  | oral 角色全流程无 crash                            |
| QA-08 | 超频 chat/recommend             | **待人工**  | 429 有友好提示                                    |
| QA-09 | 过期 token / refresh 失败         | **待人工**  | 应 logout 或弹登录                                |
| QA-10 | SSE 模拟服务端异常                   | **待人工**  | UI 不卡住，可重发                                   |


## 自动化复现命令

```bash
# QA-01
pnpm --filter @en/web type-check
pnpm --filter @en/web build

# QA-02（在 server/ 目录）
uv run alembic upgrade head
uv run python seed.py

# 后端导入冒烟
uv run python -c "from app.main import app; from ai.main import ai_app; print('OK')"

# 健康检查（需 API 已启动）
curl http://localhost:3000/health
```

## 人工验收（在「结果」列改成「通过」即可）


| ID    | 场景                         | 结果  | 验收人 / 日期 | 备注  |
| ----- | -------------------------- | --- | -------- | --- |
| QA-03 | 注册 → 登录 → refresh → 进聊天发消息 | 未测  |          |     |
| QA-04 | 推荐卡片、再推荐、刷新、切对话            | 未测  |          |     |
| QA-05 | 支付沙箱全流程                    | 未测  |          |     |
| QA-06 | 学词后推荐变化                    | 未测  |          |     |
| QA-07 | 口语：语音 + TTS + grammar      | 未测  |          |     |
| QA-08 | 超频触发 429 提示                | 未测  |          |     |
| QA-09 | token 过期 / refresh 失败      | 未测  |          |     |
| QA-10 | SSE 异常后 UI 可恢复             | 未测  |          |     |


> Markdown 预览里复选框往往不能点击。请直接改上表「结果」列：`未测` → `通过`。

## 备注

- 阶段 1～6 代码修复已完成；QA-03～10 需本地浏览器逐项验收。
- greenfield 部署失败时，检查 `alembic upgrade head` 与 `server/data/ecdict.sample.csv`。

