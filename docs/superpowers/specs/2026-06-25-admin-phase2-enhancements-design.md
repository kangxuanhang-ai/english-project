# B 端 Phase 2 增强设计（Demo 抛光 + 轻量新能力）

> 状态：**已实现** — 实现计划：[2026-06-25-admin-phase2-enhancements.md](../plans/2026-06-25-admin-phase2-enhancements.md)

## 概述

在 UI 翻新（[2026-06-25-admin-ui-redesign-design.md](./2026-06-25-admin-ui-redesign-design.md)）基础上，按 **方案 2** 做第二轮优化：

| 目标 | 内容 |
|------|------|
| **A — Demo 抛光** | 术语中文化、仪表盘待办、StatCard 跳转、知识库进度/失败提示、面包屑可点、订单未支付快捷 Tab |
| **C — 轻量新能力** | 课程封面上传、订单 CSV 导出、`GET /admin/courses/:id`、仪表盘待办数据扩展 |

**已确认决策：**

| 项 | 决策 |
|----|------|
| 方案 | **方案 2**（不做操作审计、AI 对话概览、ClickHouse） |
| 订单列表 | 增加 **未支付快捷 Tab**（`WAIT_BUYER_PAY` + `NOT_PAY`） |
| 检索示例 | 使用知识库真实可检索文案（含 **「康烜航是谁」** 等） |
| `knowledgeSearchCalls7d` | **本期不做**（无可靠埋点，避免 demo 假数据） |

**不在本期：**

- 多管理员 / RBAC、用户禁用、AI Prompt 在线编辑  
- 管理员操作审计日志  
- AI 对话统计、ClickHouse 分析  
- C 端聊天引用来源卡片  

**依赖：** 现有 `apps/admin`、`/api/v1/admin/*`、MinIO、`get_current_admin`。

---

## 架构

```
apps/admin                          server/app
├── Dashboard (+待办 Alert)    ←──  GET /admin/dashboard  （扩展字段）
├── orders/List (+Tab/导出)    ←──  GET /admin/orders/export
├── courses/Form (+封面上传)   ←──  POST /admin/courses/upload-cover
│                                  GET  /admin/courses/{id}
├── knowledge/List (+status)   ←──  GET /admin/knowledge?status=failed （已有）
└── knowledge/Search (+示例)   ←──  （仅前端）
```

待办计数**合并进现有 dashboard 响应**，不新增 `/dashboard/activity` 路由。

---

## 1. 体验抛光（A）

### 1.1 知识库 · 检索测试

**文件：** `apps/admin/src/views/knowledge/Search.tsx`

| 改动 | 说明 |
|------|------|
| Top K 文案 | `addonBefore="Top K"` → **「返回条数」**；旁加 `Tooltip`：「最多返回相似度最高的 N 条文档片段，建议 3–10」 |
| 示例问题 | FilterCard 下方 `Space wrap` 展示可点击 Tag/chip，点击填入输入框并触发检索 |

**默认示例（3 条，可配置常量）：**

1. `康烜航是谁`
2. `平台打卡规则是什么`
3. `如何购买课程`

**交互：** 点击 chip → `setQuery(text)` → `handleSearch()`。

---

### 1.2 仪表盘待办 + StatCard 跳转

**文件：** `apps/admin/src/views/Dashboard.tsx`、`apps/admin/src/components/StatCard.tsx`

**StatCard 扩展：**

```typescript
type StatCardProps = {
  // ...existing
  onClick?: () => void
}
```

- 有 `onClick` 时：`cursor: pointer`，hover 不变  
- 跳转映射：

| StatCard | 路由 |
|----------|------|
| 总用户 | `/users` |
| 今日订单额 / 今日订单数 | `/orders` |
| 知识库文档 | `/knowledge` |
| 今日 PV | `/analytics` |
| 近 7 天错误 | `/analytics`（默认 Tab 错误） |

**待办 Alert（Ant Design `Alert`，`type="warning"`，有数据才显示）：**

```tsx
{unpaidOrders > 0 && (
  <Alert
    message={`${unpaidOrders} 笔订单待支付`}
    type="warning"
    showIcon
    action={<Button size="small" onClick={() => navigate('/orders?tab=unpaid')}>去处理</Button>}
  />
)}
{failedKnowledgeDocs > 0 && (
  <Alert ... action navigate('/knowledge?status=failed') />
}
```

**Dashboard API 扩展字段（见 §2.1）：** `unpaidOrders`、`failedKnowledgeDocs`。

---

### 1.3 知识库列表

**文件：** `apps/admin/src/views/knowledge/List.tsx`

| 改动 | 说明 |
|------|------|
| 状态筛选 | `Select` 或 URL `?status=failed` 同步；后端 `list_documents` **已支持** `status` 参数 |
| processing 行 | 状态列：`pending`/`processing` 时在 Tag 旁显示 `Progress`（`percent` 无则 `status="active"`） |
| failed 行 | Tag `color="error"`；`errorMessage` 用 `Tooltip` 展示前 120 字 |

**URL 约定：**

- `/knowledge?status=failed` — 仪表盘待办跳转  
- 进入页时 `useSearchParams` 读取并初始化筛选  

---

### 1.4 订单列表 · 未支付快捷 Tab

**文件：** `apps/admin/src/views/orders/List.tsx`

在 FilterCard 上方或内部增加 `Tabs` / `Segmented`：

| Tab | 筛选逻辑 |
|-----|----------|
| 全部 | 不传 `status` |
| 待支付 | 前端两次请求合并 **或** 后端新增 `status=UNPAID` 聚合（见 §2.3 推荐 B） |

**URL：** `/orders?tab=unpaid` — 仪表盘待办跳转。

**推荐：** 后端 `list_orders` / `export` 支持 `status=UNPAID` → SQL `WHERE trade_status IN (NOT_PAY, WAIT_BUYER_PAY)`，避免前端双请求。

---

### 1.5 面包屑可点击

**文件：** `apps/admin/src/layout/AdminLayout.tsx`

- 除最后一级外，中间层级包 `onClick` → `navigate(accPath)`  
- 首页图标 → `navigate('/')`  
- 最后一级（当前页/「详情」）不可点  

---

## 2. 新能力（C）

### 2.1 仪表盘 API 扩展

**文件：** `server/app/services/admin/dashboard.py`、`packages/common/admin/index.ts`

在 `get_admin_dashboard` 返回值追加：

```python
unpaid_orders = count WHERE trade_status IN (NOT_PAY, WAIT_BUYER_PAY)
failed_knowledge_docs = count WHERE status == FAILED
```

```typescript
export interface AdminDashboard {
  // ...existing
  unpaidOrders: number
  failedKnowledgeDocs: number
}
```

**不新增路由** — 仍 `GET /api/v1/admin/dashboard`。

---

### 2.2 课程封面上传

**路由：** `POST /api/v1/admin/courses/upload-cover`  
**Auth：** `get_current_admin`  
**Body：** `multipart/form-data`，字段 `file`

**逻辑（参考 `upload_avatar`）：**

| 规则 | 值 |
|------|-----|
| 格式 | `image/jpeg`, `image/png`, `image/webp` |
| 大小 | ≤ 2MB |
| MinIO 路径 | `course-covers/{timestamp}-{safe_filename}` |
| 响应 | `{ url: previewUrl, path: databaseUrl }` — 与头像一致 |

**前端 `courses/Form.tsx`：**

- 封面字段改为：`Upload`（picture-card）+ 隐藏 `Form.Item name="url"`  
- 上传成功 → `form.setFieldValue('url', previewUrl)` + `Image` 预览  
- 仍允许手动改 url（高级场景）  
- 提示：「上传后 C 端课程列表将直接使用该图片地址」

**C 端兼容：** `course.url` 存完整 MinIO URL；现有 `imageSrc` 原样返回，无需改 C 端。

---

### 2.3 订单 CSV 导出

**路由：** `GET /api/v1/admin/orders/export`  
**Auth：** `get_current_admin`  
**Query：** 与列表相同 — `status`, `startDate`, `endDate`, `keyword`；另支持 `status=UNPAID`

**路由注册顺序（必须）：** 在 `server/app/routers/admin/orders.py` 中，`@router.get("/export")` **必须声明在** `@router.get("/{order_id}")` **之前**。FastAPI/Starlette 按注册顺序匹配，若 `{order_id}` 在前，`/orders/export` 会被当作 `order_id="export"` 导致 404 或错误详情。不允许依赖「或声明顺序」以外的变通；不得将 export 挂在 `/{order_id}` 之后。

**行为：**

- 不分页，最多 **5000** 条，按 `created_at DESC`  
- `Content-Type: text/csv; charset=utf-8`  
- 首行 BOM `\ufeff`（Excel 中文兼容）  
- `Content-Disposition: attachment; filename="orders-{YYYYMMDD}.csv"`

**CSV 列：**

| 列名 | 字段 |
|------|------|
| 订单号 | outTradeNo |
| 用户 | userName |
| 手机号 | userPhone |
| 金额 | amount |
| 状态 | tradeStatus → 中文（用 TRADE_STATUS_MAP 逻辑） |
| 创建时间 | createdAt → **北京时间** `YYYY-MM-DD HH:mm:ss` |

**实现：** 新增 `server/app/services/admin/orders.py` → `export_orders_csv()`；在 `orders.py` 路由文件中注册 `GET /export`（见上文 **路由注册顺序**）。

**前端：** 订单列表 FilterCard 右侧 `Button`「导出 CSV」— 用当前筛选条件拼 query，`window.open` 或 `fetch` + blob download；请求头带 JWT（Axios blob 或 `<a download>` + token query 不推荐 — 用 blob fetch）。

---

### 2.4 课程详情 API

**路由：** `GET /api/v1/admin/courses/{course_id}`  
**Service：** `get_course(db, course_id) -> dict | None`  
**404：** 课程不存在  

**前端：** `courses/Form.tsx` 编辑模式改为：

```typescript
useQuery({
  queryKey: ['admin-course', id],
  queryFn: () => fetchCourse(id!),
  enabled: isEdit,
})
```

删除「拉 list 100 条再 find」的 workaround。

---

### 2.5 订单 `UNPAID` 聚合状态（后端小扩展）

**文件：** `list_orders`、`export_orders_csv`

当 `status=UNPAID`：

```python
query = query.where(PaymentRecord.trade_status.in_([TradeStatus.NOT_PAY, TradeStatus.WAIT_BUYER_PAY]))
```

**前端 Tab「待支付」** 传 `status=UNPAID`。

---

## 3. 类型与 API 客户端

**文件：** `packages/common/admin/index.ts`、`apps/admin/src/apis/admin.ts`

新增/修改：

```typescript
fetchCourse(id: string)
uploadCourseCover(file: File)
exportOrders(params: OrderListParams): Promise<Blob>  // 或返回 blob URL
```

`AdminDashboard` 增加 `unpaidOrders`, `failedKnowledgeDocs`。

---

## 4. 答辩 Demo 脚本（5 分钟）

1. **登录** — 展示 Indigo 品牌登录页  
2. **仪表盘** — 指出待办 Alert → 点击跳转未支付订单  
3. **订单** — Tab 待支付 → **导出 CSV**  
4. **课程** — 新建课程 → **上传封面** → 保存  
5. **知识库** — 检索测试 → 点示例「康烜航是谁」→ 展示相似度结果  

---

## 5. 文件清单

| 文件 | 动作 |
|------|------|
| `server/app/services/admin/dashboard.py` | Modify — 待办计数 |
| `server/app/services/admin/orders.py` | Modify — UNPAID + export CSV |
| `server/app/services/admin/courses.py` | Modify — get_course + upload_cover |
| `server/app/routers/admin/orders.py` | Modify — GET /export |
| `server/app/routers/admin/courses.py` | Modify — GET /{id}, POST /upload-cover |
| `packages/common/admin/index.ts` | Modify — 类型 |
| `apps/admin/src/apis/admin.ts` | Modify — 新 API |
| `apps/admin/src/components/StatCard.tsx` | Modify — onClick |
| `apps/admin/src/layout/AdminLayout.tsx` | Modify — 面包屑 |
| `apps/admin/src/views/Dashboard.tsx` | Modify — Alert + 跳转 |
| `apps/admin/src/views/orders/List.tsx` | Modify — Tab + 导出 |
| `apps/admin/src/views/courses/Form.tsx` | Modify — 封面上传 + fetchCourse |
| `apps/admin/src/views/knowledge/List.tsx` | Modify — status 筛选 + Progress |
| `apps/admin/src/views/knowledge/Search.tsx` | Modify — 返回条数 + 示例 |

---

## 6. 验收标准

1. 检索页无裸「Top K」；Tooltip + 3 条示例可一键检索  
2. 仪表盘有待办 Alert（有未支付/失败文档时）；StatCard 可跳转  
3. 订单 Tab「待支付」+ CSV 导出（Excel 打开中文正常）  
4. 课程编辑页 `GET /courses/:id`；封面上传后表单 preview + 保存成功  
5. 知识库 `?status=failed` 筛选可用；processing 有 Progress  
6. 面包屑中间层级可点击  
7. `pnpm --filter @en/admin build` 通过；手动 smoke 上述 Demo 脚本  

---

## 7. 参考

- [2026-06-24-admin-knowledge-base-design.md](./2026-06-24-admin-knowledge-base-design.md) — 原 B 端范围  
- [2026-06-25-admin-ui-redesign-design.md](./2026-06-25-admin-ui-redesign-design.md) — UI 基线  
- `server/app/services/user.py` — `upload_avatar` MinIO 模式  
- `server/app/services/knowledge/documents.py` — `list_documents(status=)` 已存在  
