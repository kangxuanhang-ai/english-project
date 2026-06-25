# B 端 Phase 2 增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 B 端 UI 翻新基础上，完成 Demo 抛光（术语、待办、跳转）与 3 项新能力（封面上传、订单 CSV、课程 GET），并扩展 dashboard 待办计数。

**Architecture:** 先后端（dashboard 字段、UNPAID 筛选、export CSV、course GET/upload）再 `@en/common` 类型与 admin API 客户端，最后逐页改 React。CSV 导出需在 middleware 跳过 envelope；`/export` 路由必须注册在 `/{order_id}` 之前。

**Tech Stack:** FastAPI, SQLAlchemy, MinIO, React 18, Ant Design 5, TanStack Query, `@en/common`

**设计文档:** [2026-06-25-admin-phase2-enhancements-design.md](../specs/2026-06-25-admin-phase2-enhancements-design.md)

**测试说明:** 无 vitest/pytest；各 Task 用 `pnpm --filter @en/admin build` + 浏览器 + 可选 `curl` 验证 CSV。

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `server/app/middleware.py` | Modify | 跳过 `/api/v1/admin/orders/export` envelope |
| `server/app/services/admin/dashboard.py` | Modify | `unpaidOrders`, `failedKnowledgeDocs` |
| `server/app/services/admin/orders.py` | Modify | `UNPAID` 筛选 + `export_orders_csv` |
| `server/app/services/admin/courses.py` | Modify | `get_course`, `upload_course_cover` |
| `server/app/routers/admin/orders.py` | Modify | `GET /export`（在 `/{order_id}` 前） |
| `server/app/routers/admin/courses.py` | Modify | `GET /{id}`, `POST /upload-cover` |
| `packages/common/admin/index.ts` | Modify | `AdminDashboard` 扩展 + 类型 |
| `apps/admin/src/apis/admin.ts` | Modify | `fetchCourse`, `uploadCourseCover`, `downloadOrdersCsv` |
| `apps/admin/src/components/StatCard.tsx` | Modify | `onClick` |
| `apps/admin/src/layout/AdminLayout.tsx` | Modify | 面包屑可点击 |
| `apps/admin/src/views/Dashboard.tsx` | Modify | Alert + StatCard 跳转 |
| `apps/admin/src/views/orders/List.tsx` | Modify | Tab + 导出 |
| `apps/admin/src/views/courses/Form.tsx` | Modify | 封面上传 + `fetchCourse` |
| `apps/admin/src/views/knowledge/List.tsx` | Modify | status URL + Progress |
| `apps/admin/src/views/knowledge/Search.tsx` | Modify | 返回条数 + 示例 chip |
| `apps/admin/src/views/analytics/Overview.tsx` | Modify | 支持 `?tab=errors` |
| `docs/superpowers/specs/2026-06-25-admin-phase2-enhancements-design.md` | Modify | 状态 → 已评审 |

---

## Phase 1 — 后端

> **完成标准:** dashboard 新字段可 curl；`/orders/export` 返回 CSV；`UNPAID` 筛选有效；course GET/upload 可用。

---

### Task 1.1: Dashboard 待办计数

**Files:**
- Modify: `server/app/services/admin/dashboard.py`
- Modify: `packages/common/admin/index.ts`

- [ ] **Step 1:** 在 `get_admin_dashboard` 追加查询：

```python
from app.models.knowledge import DocumentStatus, KnowledgeDocument

unpaid_orders = (
    await db.execute(
        select(func.count(PaymentRecord.id)).where(
            PaymentRecord.trade_status.in_([
                TradeStatus.NOT_PAY,
                TradeStatus.WAIT_BUYER_PAY,
            ])
        )
    )
).scalar() or 0

failed_knowledge_docs = (
    await db.execute(
        select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.status == DocumentStatus.FAILED.value
        )
    )
).scalar() or 0
```

- [ ] **Step 2:** return dict 增加 `"unpaidOrders": unpaid_orders`, `"failedKnowledgeDocs": failed_knowledge_docs`

- [ ] **Step 3:** `AdminDashboard` 接口增加同名字段

- [ ] **Step 4:** 验证（server 运行中）

Run: `curl -H "Authorization: Bearer <admin_token>" http://localhost:3000/api/v1/admin/dashboard`
Expected: `data.unpaidOrders` 和 `data.failedKnowledgeDocs` 为数字

---

### Task 1.2: 订单 UNPAID 聚合筛选

**Files:**
- Modify: `server/app/services/admin/orders.py`

- [ ] **Step 1:** 抽取 `_apply_order_filters(query, count_query, status, ...)` 或在 `list_orders` 内修改 status 分支：

```python
if status == "UNPAID":
    cond = PaymentRecord.trade_status.in_([
        TradeStatus.NOT_PAY,
        TradeStatus.WAIT_BUYER_PAY,
    ])
    query = query.where(cond)
    count_query = count_query.where(cond)
elif status:
    try:
        trade_status = TradeStatus(status)
        ...
```

- [ ] **Step 2:** 验证列表

Run: `curl ".../admin/orders?status=UNPAID&page=1&pageSize=10" -H "Authorization: Bearer ..."`
Expected: 仅 NOT_PAY / WAIT_BUYER_PAY 订单

---

### Task 1.3: 订单 CSV 导出 + middleware 跳过

**Files:**
- Modify: `server/app/services/admin/orders.py`
- Modify: `server/app/routers/admin/orders.py`
- Modify: `server/app/middleware.py`

- [ ] **Step 1:** 在 `orders.py` service 新增常量与映射：

```python
TRADE_STATUS_LABELS = {
    "NOT_PAY": "未支付",
    "WAIT_BUYER_PAY": "待支付",
    "TRADE_CLOSED": "已关闭",
    "TRADE_SUCCESS": "支付成功",
    "TRADE_FINISHED": "已完成",
}
EXPORT_LIMIT = 5000
```

- [ ] **Step 2:** 实现 `export_orders_csv(db, *, status, start_date, end_date, keyword) -> str`：

```python
import csv
from io import StringIO
from zoneinfo import ZoneInfo

CN_TZ = ZoneInfo("Asia/Shanghai")

def _format_cn_time(iso: str | None) -> str:
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CN_TZ).strftime("%Y-%m-%d %H:%M:%S")
```

- 复用与 `list_orders` 相同的 filter 逻辑（含 `UNPAID`）
- `query.order_by(PaymentRecord.created_at.desc()).limit(EXPORT_LIMIT)`
- `csv.writer` 写 header + rows
- 返回 `"\ufeff" + buf.getvalue()`

- [ ] **Step 3:** 在 `routers/admin/orders.py` **文件顶部路由区**，在 `@router.get("/{order_id}")` **之前** 添加：

```python
from fastapi.responses import Response

@router.get("/export")
async def admin_export_orders(
    status: str | None = None,
    startDate: str | None = None,
    endDate: str | None = None,
    keyword: str | None = None,
    _admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    csv_text = await export_orders_csv(
        db,
        status=status,
        start_date=startDate,
        end_date=endDate,
        keyword=keyword,
    )
    filename = f"orders-{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_text.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 4:** `middleware.py` 在 pay/notify 跳过之后追加：

```python
if request.url.path.startswith("/api/v1/admin/orders/export"):
    return await call_next(request)
```

- [ ] **Step 5:** 验证

Run: `curl -o orders.csv -H "Authorization: Bearer ..." "http://localhost:3000/api/v1/admin/orders/export?status=UNPAID"`
Expected: 文件为 CSV，Excel 打开中文列名正常；**不是** JSON envelope

---

### Task 1.4: 课程 GET + 封面上传

**Files:**
- Modify: `server/app/services/admin/courses.py`
- Modify: `server/app/routers/admin/courses.py`

- [ ] **Step 1:** `courses.py` service 新增：

```python
async def get_course(db: AsyncSession, course_id: str) -> dict | None:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    return _course_item(course) if course else None
```

- [ ] **Step 2:** 新增 `upload_course_cover(file)`（复制 `upload_avatar` 模式，改动如下）：

```python
ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_COVER_BYTES = 2 * 1024 * 1024

async def upload_course_cover(file) -> dict:
    if file.content_type not in ALLOWED_COVER_TYPES:
        raise ValueError("仅支持 JPG/PNG/WebP 格式")
    content = await file.read()
    if len(content) > MAX_COVER_BYTES:
        raise ValueError("封面不能超过 2MB")
    safe_name = re.sub(r"[^\w.\-]", "_", file.filename or "cover.png")
    file_name = f"course-covers/{int(time.time() * 1000)}-{safe_name}"
    # put_object ... 同 upload_avatar
    return {"url": preview_url, "path": object_path}
```

- [ ] **Step 3:** router 注册（**顺序**：`upload-cover` 与 `GET ""` 之后，`PUT /{course_id}` 之前无冲突；`GET /{course_id}` 放在 list 之后）：

```python
from fastapi import File, UploadFile

@router.get("/{course_id}")
async def admin_get_course(...):
    data = await get_course(db, course_id)
    if not data:
        raise HTTPException(status_code=404, detail="课程不存在")
    return {"data": data, "code": 200, "message": "查询成功"}

@router.post("/upload-cover")
async def admin_upload_course_cover(
    file: UploadFile = File(...),
    _admin: dict = Depends(get_current_admin),
):
    try:
        data = await upload_course_cover(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"data": data, "code": 200, "message": "上传成功"}
```

> **注意:** `POST /upload-cover` 是静态路径，与 `/{course_id}` 不冲突；`GET /{course_id}` 不会吃掉 `upload-cover`。

- [ ] **Step 4:** 验证

Run: `curl -H "Authorization: Bearer ..." http://localhost:3000/api/v1/admin/courses/<id>`
Expected: 单条课程 JSON envelope

---

## Phase 2 — API 客户端与类型

---

### Task 2.1: `@en/common` + `admin.ts`

**Files:**
- Modify: `packages/common/admin/index.ts`
- Modify: `apps/admin/src/apis/admin.ts`

- [ ] **Step 1:** 确认 `AdminDashboard` 含 `unpaidOrders`, `failedKnowledgeDocs`

- [ ] **Step 2:** 新增 API 函数：

```typescript
export function fetchCourse(id: string) {
  return api.get<unknown, ApiResponse<AdminCourse>>(`/admin/courses/${id}`)
}

export function uploadCourseCover(file: File) {
  const form = new FormData()
  form.append('file', file)
  return api.post<unknown, ApiResponse<{ url: string; path: string }>>(
    '/admin/courses/upload-cover',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
}

export type OrderExportParams = {
  status?: string
  startDate?: string
  endDate?: string
  keyword?: string
}

export async function downloadOrdersCsv(params: OrderExportParams) {
  const res = await axios.get('/api/v1/admin/orders/export', {
    params,
    responseType: 'blob',
    headers: { Authorization: `Bearer ${useUserStore.getState().accessToken}` },
  })
  const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `orders-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
```

> `downloadOrdersCsv` 用裸 `axios` + `responseType: 'blob'`，避免 envelope 拦截器破坏二进制。

- [ ] **Step 3:** 验证编译

Run: `pnpm --filter @en/admin build`
Expected: PASS

---

## Phase 3 — 前端体验抛光

---

### Task 3.1: StatCard onClick

**Files:**
- Modify: `apps/admin/src/components/StatCard.tsx`

- [ ] **Step 1:** 增加 optional `onClick?: () => void`

- [ ] **Step 2:** 根 `Card` 加 `onClick={onClick}` 与 `style={{ cursor: onClick ? 'pointer' : undefined }}`

---

### Task 3.2: Dashboard 待办 + 跳转

**Files:**
- Modify: `apps/admin/src/views/Dashboard.tsx`

- [ ] **Step 1:** `import { Alert, Button } from 'antd'` + `useNavigate`

- [ ] **Step 2:** PageShell 下第一块渲染 Alert（`unpaidOrders` / `failedKnowledgeDocs` > 0）

- [ ] **Step 3:** 各 StatCard 传入 `onClick={() => navigate(...)}`（见 spec §1.2 映射；错误 → `/analytics?tab=errors`）

---

### Task 3.3: Analytics 支持 tab query

**Files:**
- Modify: `apps/admin/src/views/analytics/Overview.tsx`

- [ ] **Step 1:** `useSearchParams` 读取 `tab`，初始化 `Tabs activeKey`

- [ ] **Step 2:** `onChange` 时 `setSearchParams({ tab: key })`

---

### Task 3.4: 面包屑可点击

**Files:**
- Modify: `apps/admin/src/layout/AdminLayout.tsx`

- [ ] **Step 1:** 重写 `buildBreadcrumbs` 返回 `{ title, path? }[]`

- [ ] **Step 2:** 渲染时最后一项纯文本；有 `path` 的项包 `<span onClick={() => navigate(path)} style={{ cursor: 'pointer' }}>`；首页图标 `navigate('/')`

---

### Task 3.5: 知识库检索页

**Files:**
- Modify: `apps/admin/src/views/knowledge/Search.tsx`

- [ ] **Step 1:** 常量：

```typescript
const SEARCH_EXAMPLES = ['康烜航是谁', '平台打卡规则是什么', '如何购买课程']
```

- [ ] **Step 2:** `InputNumber` → `addonBefore="返回条数"` + `Tooltip title="最多返回相似度最高的 N 条文档片段，建议 3–10"`

- [ ] **Step 3:** FilterCard 下示例 Tag，`onClick` 调用 `runSearch(text)`（setQuery + handleSearch）

- [ ] **Step 4:** 将 `handleSearch` 改为接受可选 `q` 参数避免 state 延迟

---

### Task 3.6: 知识库列表 status + Progress

**Files:**
- Modify: `apps/admin/src/views/knowledge/List.tsx`

- [ ] **Step 1:** `useSearchParams` — 初始化 `status` from `?status=failed`

- [ ] **Step 2:** FilterCard 加 `Select` status 筛选，变更时 sync URL

- [ ] **Step 3:** 状态列 render：

```tsx
if (v === 'pending' || v === 'processing') {
  return (
    <Space>
      <Tag color={meta.color}>{meta.label}</Tag>
      <Progress type="line" percent={undefined} size="small" style={{ width: 80 }} status="active" />
    </Space>
  )
}
if (v === 'failed' && record.errorMessage) {
  return (
    <Tooltip title={record.errorMessage.slice(0, 120)}>
      <Tag color="error">{meta.label}</Tag>
    </Tooltip>
  )
}
```

- [ ] **Step 4:** `fetchKnowledgeDocs` 传入 `status` param（API 已支持）

---

### Task 3.7: 订单 Tab + CSV 导出

**Files:**
- Modify: `apps/admin/src/views/orders/List.tsx`

- [ ] **Step 1:** `useSearchParams` — `tab=unpaid` → `status=UNPAID`

- [ ] **Step 2:** FilterCard 上方 `Segmented`：`全部` | `待支付`

- [ ] **Step 3:** FilterCard 内右侧 `Button`「导出 CSV」→ `downloadOrdersCsv({ status, startDate, endDate, keyword: search })`

- [ ] **Step 4:** 浏览器验证 Tab 与导出

---

## Phase 4 — 课程表单

---

### Task 4.1: fetchCourse + 封面上传 UI

**Files:**
- Modify: `apps/admin/src/views/courses/Form.tsx`

- [ ] **Step 1:** 替换 edit 数据加载：

```typescript
const { data: courseData } = useQuery({
  queryKey: ['admin-course', id],
  queryFn: () => fetchCourse(id!),
  enabled: isEdit,
})

useEffect(() => {
  if (courseData?.data) form.setFieldsValue(courseData.data)
}, [courseData, form])
```

- 删除 `admin-courses-edit` list 100 查询

- [ ] **Step 2:** 封面区：

```tsx
<Form.Item name="url" label="封面" rules={[{ required: true }]} extra="上传后 C 端课程列表将直接使用该图片地址">
  <Input placeholder="上传或粘贴图片 URL" />
</Form.Item>
<Upload
  listType="picture-card"
  showUploadList={false}
  beforeUpload={(file) => {
    void uploadCourseCover(file as File).then((res) => {
      form.setFieldValue('url', res.data.url)
      message.success('封面上传成功')
    }).catch(() => message.error('上传失败'))
    return false
  }}
>
  {form.getFieldValue('url') ? (
    <img src={form.getFieldValue('url')} alt="cover" style={{ width: '100%' }} />
  ) : (
    '+ 上传封面'
  )}
</Upload>
```

- [ ] **Step 3:** 验证新建/编辑课程 + C 端列表封面显示

---

## Phase 5 — 终验

---

### Task 5.1: 构建 + Demo 脚本

- [ ] **Step 1:** 构建

Run: `pnpm --filter @en/admin build`
Expected: PASS

- [ ] **Step 2:** grep 确认无裸 Top K

Run: `rg 'Top K' apps/admin`
Expected: 无匹配

- [ ] **Step 3:** 手动走通 spec §4 Demo 脚本（5 步）

- [ ] **Step 4:** 更新 spec 状态

```markdown
> 状态：**已评审** — 实现计划：[2026-06-25-admin-phase2-enhancements.md](../plans/2026-06-25-admin-phase2-enhancements.md)
```

- [ ] **Step 5:** 可选 commit（仅用户要求时）

---

## Spec Coverage Self-Review

| Spec 章节 | Task |
|-----------|------|
| §1.1 检索示例 + 返回条数 | 3.5 |
| §1.2 Dashboard Alert + StatCard | 1.1, 3.1, 3.2 |
| §1.3 知识库 status/Progress | 3.6 |
| §1.4 订单 Tab UNPAID | 1.2, 3.7 |
| §1.5 面包屑 | 3.4 |
| §2.1 dashboard 字段 | 1.1 |
| §2.2 封面上传 | 1.4, 4.1 |
| §2.3 CSV export + 路由顺序 + middleware | 1.3 |
| §2.4 GET course | 1.4, 4.1 |
| §2.5 UNPAID | 1.2 |
| §6 验收标准 | 5.1 |

**无遗漏。**

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-25-admin-phase2-enhancements.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — 每个 Phase 派子 agent，Task 间 review  
2. **Inline Execution** — 本会话按 Phase 直接实现，每 Phase checkpoint

**Which approach?**
