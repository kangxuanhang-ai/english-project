# Phase 3 — Agent 评测 Dataset + Experiment

**日期**: 2026-06-29  
**状态**: 已实现  
**依赖**: Phase 1（create_agent + tracing）、Phase 2（Hub prompt）

---

## 目标

对 `normal` 角色 agent 建立可重复回归评测：工具调用准确率、JSON 防泄漏、延迟。

---

## Dataset

- 名称：`english-agent-normal-v1`
- 规模：23 条（`server/ai/data/agent_eval_cases.py`）
- LangSmith 项目：`english-agent-eval`（`LANGCHAIN_EVAL_PROJECT`）

| 类别 | 条数 | 评分点 |
|------|------|--------|
| word_lookup | 4 | 必须调 word_lookup |
| grammar_check | 3 | 必须调 grammar_check |
| course_recommendation | 4 | 必须调 course_recommendation + 部分防 JSON 泄漏 |
| knowledge_search | 4 | 必须调 knowledge_search |
| course_purchase | 2 | 必须调 course_purchase |
| progress_query | 2 | 必须调 progress_query |
| negative_no_knowledge | 3 | 禁止 knowledge_search（含天气负例） |
| no_json_leak | 1 | 推荐 + 防泄漏 |

---

## Evaluators

| Key | 说明 |
|-----|------|
| `tool_accuracy` | 期望工具是否调用 / 禁止工具是否未调用 |
| `no_json_leak` | 推荐场景回复是否泄漏 `{ "courses":` 等 JSON |
| `latency_ok` | 单条是否在 `max_latency_ms`（默认 45s）内 |
| `p95_latency_ms` | Experiment 汇总 P95 延迟 |

---

## 命令

```powershell
cd server

# 1. 创建 dataset（首次或 --force 重建）
uv run python scripts/create_agent_eval_dataset.py

# 2. 跑全量 experiment（约 23 条 × DeepSeek，需数分钟，会消耗 API）
uv run python scripts/run_agent_eval.py

# 3. 快速试跑 3 条
uv run python scripts/run_agent_eval.py --limit 3
```

前置：`.env` 配置 `LANGCHAIN_API_KEY`、`DEEPSEEK_API_KEY`、数据库可用（工具会查库）。

---

## 新增文件

| 文件 | 说明 |
|------|------|
| `ai/data/agent_eval_cases.py` | 23 条用例定义 |
| `ai/services/agent_eval.py` | 运行单条 + evaluators |
| `scripts/create_agent_eval_dataset.py` | 推送 dataset 到 LangSmith |
| `scripts/run_agent_eval.py` | 跑 experiment |

---

## 验收

- [x] dataset 可创建
- [ ] baseline experiment 可重复执行（需 DeepSeek 配额）
- [ ] LangSmith UI 可对比两次 experiment 分数
- [ ] 答辩可展示 Datasets & Experiments 页面

---

## 查看结果

LangSmith → **Datasets & Experiments** → `english-agent-normal-v1` → 最新 experiment → 各 evaluator 分数与 trace。
