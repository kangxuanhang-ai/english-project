# 阶段一设计：稳定性修复

> 日期：2026-06-23
> 范围：安全漏洞修复 + 前端稳定性 + 后端稳定性
> 目标：项目可安全上线，答辩无明显 bug

---

## 1. 安全修复

### 1.1 密码存储 — bcrypt 兼容迁移

**现状**：前端 MD5 哈希后直接存库，服务端无二次哈希。数据库泄露 = 所有密码暴露。

**方案**：服务端收到前端 MD5 哈希后，用 bcrypt 再哈希一层存储。登录时根据密码格式判断走哪条路径：

```python
# server/app/services/user.py — login
if user.password.startswith("$2b$"):
    # 已迁移用户，bcrypt 验证
    if not bcrypt.checkpw(md5_hash.encode(), user.password.encode()):
        raise ValueError("密码错误")
else:
    # 未迁移用户，MD5 直接比较
    if user.password != md5_hash:
        raise ValueError("密码错误")
    # 首次登录成功后静默升级为 bcrypt
    user.password = bcrypt.hashpw(md5_hash.encode(), bcrypt.gensalt()).decode()
    await db.commit()

# server/app/services/user.py — register
hashed = bcrypt.hashpw(md5_hash.encode(), bcrypt.gensalt()).decode()
```

- 新增依赖：`bcrypt`（添加到 `pyproject.toml`）
- 修改文件：`server/app/services/user.py`（注册 + 登录）
- 存量用户无感知迁移，新用户直接走 bcrypt

### 1.2 `.gitignore` 补全

**现状**：`.gitignore` 只有 `node_modules`，`.env` 文件未被排除。

**方案**：在 `.gitignore` 中添加：
```
.env
.env.*
server/.env
*.pem
*.key
```

**经核实**：`server/.env` 当前未被 Git 追踪（`git ls-files` 无记录），不存在历史泄露风险。此修复为预防性措施。

### 1.3 Socket.IO CORS 收紧

**现状**：`cors_allowed_origins="*"`，任意网站可建立 WebSocket 连接。

**方案**：从配置读取允许的前端域名列表：
```python
# server/app/services/socket.py
from app.config import settings
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.cors_origins,  # 新增配置项
)
```

- `server/.env` 新增 `CORS_ORIGINS=http://localhost:8080,https://yourdomain.com`
- `server/app/config.py` 新增字段定义：
```python
cors_origins: list[str] = Field(default=["http://localhost:8080"], alias="CORS_ORIGINS")
```

### 1.4 头像上传鉴权 + 文件校验

**现状**：`upload-avatar` 无鉴权，匿名用户可上传任意文件。文件名未清理，存在路径遍历风险。

**方案**：
1. 路由添加 `Depends(get_current_user)`
2. 文件名校验：去掉路径分隔符，只保留字母数字和扩展名
3. Content-type 校验：只允许 `image/jpeg`、`image/png`、`image/webp`
4. 文件大小限制：保持现有 5MB 限制（`1024 * 1024 * 5`）

```python
# server/app/routers/user.py — 路由层添加鉴权（当前无鉴权）
@router.post("/upload-avatar")
async def upload(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    """上传头像。添加鉴权，防止匿名上传"""
    try:
        result = await upload_avatar(file)
        return {"data": result, "code": 200, "message": "上传成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# server/app/services/user.py — 服务层添加校验（当前签名为 upload_avatar(file)）
import re
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

async def upload_avatar(file):  # 签名不变，内部添加校验
    if file.content_type not in ALLOWED_TYPES:
        raise ValueError("仅支持 JPG/PNG/WebP 格式")
    safe_name = re.sub(r'[^\w.\-]', '_', file.filename or "avatar.png")
    file_name = f"{int(time.time() * 1000)}-{safe_name}"
    # ...
```

- 修改文件：`server/app/routers/user.py`（鉴权）、`server/app/services/user.py`（校验+文件名清理）
- 注意：服务函数签名保持 `upload_avatar(file)` 不变，`db` 参数当前不需要（头像 URL 在 update_user 中保存）

### 1.5 XSS 修复 — v-html 消毒

**现状**：4 处 `v-html` 直接渲染 API 返回的 HTML，无消毒。

**方案**：使用已有的 `dompurify` 依赖：
```typescript
import DOMPurify from 'dompurify'

// 在模板中用函数替代直接 v-html
<div v-html="sanitize(item.translation)" />

function sanitize(html: string): string {
    return DOMPurify.sanitize(html)
}
```

- 修改文件：
  - `apps/web/src/views/Course/Learn/index.vue`（第 62、67 行）
  - `apps/web/src/views/WordBook/index.vue`（第 34 行）
  - `apps/web/src/components/Search/index.vue`（第 14 行）

### 1.6 登录/注册限速

**现状**：主服务端无任何 rate limiting，可被暴力破解。

**方案**：复用 `ai/rate_limit.py` 的 slowapi pattern：
```python
# server/app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# server/app/routers/user.py
@limiter.limit("5/minute")
@router.post("/login")
async def login(...): ...

@limiter.limit("3/minute")
@router.post("/register")
async def register(...): ...
```

- 修改文件：`server/app/main.py`、`server/app/routers/user.py`

### 1.7 JWT 密钥 + Token 时效

**现状**：SECRET_KEY 是短字符串，Access Token 10 秒过期。

**方案**：
- SECRET_KEY 改为 32 字节随机数据（提供生成脚本）
- Access Token 改为 15 分钟过期
- Refresh Token 保持 7 天不变
- **前端无需改动**：`ensureValidToken()` 的 5 秒 buffer 在 15 分钟下完全够用

```python
# server/app/services/auth.py
access_token_expires = timedelta(minutes=15)  # 原来是 seconds=10
```

- 修改文件：`server/.env`、`server/app/services/auth.py`

### 1.8 支付宝回调地址配置化

**现状**：`return_url` 硬编码为 `http://localhost:8080/courses/index`。

**方案**：从配置读取：
```python
# server/app/config.py
alipay_return_url: str = Field(default="http://localhost:8080/courses/index", alias="ALIPAY_RETURN_URL")

# server/app/services/pay.py
request.return_url = settings.alipay_return_url
```

- 修改文件：`server/app/config.py`、`server/app/services/pay.py`、`server/.env`

### 1.9 CORS 中间件

**现状**：两个 FastAPI 应用都没有 CORS 中间件。

**方案**：
```python
from fastapi.middleware.cors import CORSMiddleware

# server/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# server/ai/main.py — 同上
```

- 复用 1.3 中的 `cors_origins` 配置
- 修改文件：`server/app/main.py`、`server/ai/main.py`

---

## 2. 前端稳定性修复

### 2.1 Three.js 资源清理

**现状**：`Hologram.vue` 和 `ModelViewer.vue` 无 `onUnmounted` 清理，WebGL 上下文泄漏，动画循环持续运行。

**方案**：
```typescript
onUnmounted(() => {
    renderer.dispose()
    controls.dispose()
    cancelAnimationFrame(animationId)
    // 清理场景中的几何体和材质
    scene.traverse((obj) => {
        if (obj.isMesh) {
            obj.geometry.dispose()
            if (Array.isArray(obj.material)) {
                obj.material.forEach(m => m.dispose())
            } else {
                obj.material.dispose()
            }
        }
    })
})
```

- 修改文件：`apps/web/src/views/Home/components/Hologram.vue`、`apps/web/src/components/Login/ModelViewer.vue`

### 2.2 事件监听器清理

**现状**：`Login/index.vue` 和 `Search/index.vue` 的 `window.addEventListener` 每次挂载新增，从不清理。

**方案**：在 `<script setup>` 中用生命周期钩子：
```typescript
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
```

- 修改文件：`apps/web/src/components/Login/index.vue`、`apps/web/src/components/Search/index.vue`

### 2.3 GSAP ScrollTrigger 清理

**现状**：`Home/index.vue` 注册了 5 个 ScrollTrigger 实例，无 `onUnmounted` 清理。

**方案**：当前代码用 `gsap.fromTo(..., { scrollTrigger: {...} })` 隐式创建 ScrollTrigger，无法收集实例引用。改用 `ScrollTrigger.getAll()` 批量清理：
```typescript
onUnmounted(() => {
    ScrollTrigger.getAll().forEach(t => t.kill())
})
```

- 修改文件：`apps/web/src/views/Home/index.vue`

### 2.4 Store 非空断言修复

**现状**：`user.ts` 中 14 处 `user.value!`，logout 后调用会 TypeError。

**方案**：所有方法添加 null 检查：
```typescript
const updateToken = (newToken: Token) => {
    if (!user.value) return
    user.value.token = newToken
}
```

- 影响方法：`updateToken`、`updateUserWordNumber`、`updateUser`、`getUpdateUserInfo`
- 修改文件：`apps/web/src/stores/user.ts`

### 2.5 路由守卫

**现状**：直接访问 `/chat`、`/setting` 可绕过登录。

**方案**：添加 `beforeEach` 守卫，通过路由 meta 标记需要登录的路由：
```typescript
// router/index.ts
const routes = [
    { path: '/', component: Home },
    { path: '/chat/:role/:conversationId?', component: Chat, meta: { requiresAuth: true } },
    { path: '/setting/index', component: Setting, meta: { requiresAuth: true } },
    { path: '/courses/index', component: Course },  // 不需要登录，可浏览
    { path: '/courses/learn/:courseId/:title', component: Learn, meta: { requiresAuth: true } },
]

router.beforeEach((to) => {
    if (to.meta.requiresAuth && !useUserStore().getAccessToken) {
        // 弹出登录框或重定向
        return { path: '/' }
    }
})
```

- `/courses/index` 不加守卫，让用户能浏览课程，购买时再拦截
- 修改文件：`apps/web/src/router/index.ts` 及各子路由文件

### 2.6 错误处理补全

**现状**：多个页面 API 调用无 try/catch，失败时无用户反馈。

**方案**：统一模式 — try/catch + ElMessage.error：
```typescript
const getList = async () => {
    try {
        isLoading.value = true
        const res = await apiCall()
        list.value = res.data
    } catch (error) {
        ElMessage.error('加载失败，请稍后重试')
    } finally {
        isLoading.value = false
    }
}
```

- 修改文件：
  - `apps/web/src/views/Course/index.vue` — `getList()`
  - `apps/web/src/views/Course/components/Pay.vue` — `onConfirm()`
  - `apps/web/src/views/Course/Learn/index.vue` — `getWordListData()`
  - `apps/web/src/views/WordBook/index.vue` — `getList()`
  - `apps/web/src/views/Chat/components/RoleList.vue` — `getChatMode()`
  - `apps/web/src/views/Chat/components/ConversationList.vue` — `handleCreate()`、`deleteConversation()`
  - `apps/web/src/stores/chat.ts` — `setRole()`、`createConversation()`、`deleteConversation()`

### 2.7 聊天自动滚动修复

**现状**：`scrollToBottom()` 有 `isNearBottom` 检查，用户往上滚动后发新消息不会自动滚到底部。

**方案**：单函数 + `force` 参数：
```typescript
function scrollToBottom(force = false) {
    const el = chatRef.value?.parentElement?.parentElement
    if (!el) return
    if (!force) {
        const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 150
        if (!isNearBottom) return
    }
    nextTick(() => chatRef.value?.scrollIntoView({ behavior: 'smooth' }))
}
```

- `sendMessage()` 中推送消息后调用 `scrollToBottom(true)`
- SSE 流式回调中调用 `scrollToBottom()`（默认 false）
- 修改文件：`apps/web/src/views/Chat/components/ChatArea.vue`

### 2.8 JWT Token 解析容错

**现状**：`ensureValidToken()` catch 块返回原始 token，损坏 token 导致无限 401 循环。

**方案**：catch 返回 `null`：
```typescript
try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    // ...
} catch {
    return null  // 原来是 return token
}
```

- 修改文件：`apps/web/src/apis/auth/index.ts`

### 2.9 重型库按需加载

**现状**：Three.js（~600KB）和 GSAP（~100KB）在首页全量引入。

**方案**：在 `onMounted` 中用 `import()` 延迟加载，加 `isLoaded` 状态防止空白闪烁：
```typescript
const isLoaded = ref(false)

onMounted(async () => {
    const THREE = await import('three')
    const { OrbitControls } = await import('three/addons/controls/OrbitControls.js')
    const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js')
    // 初始化场景...
    isLoaded.value = true
})
```
模板中 canvas 加 `v-if="isLoaded"`，加载完成前显示骨架屏或 loading 动画。

- GSAP 同理：`const gsap = (await import('gsap')).default`
- 修改文件：`apps/web/src/views/Home/components/Hologram.vue`、`apps/web/src/components/Login/ModelViewer.vue`、`apps/web/src/views/Home/index.vue`

---

## 3. 后端稳定性修复

### 3.1 数据库连接池健康检查

**现状**：无 `pool_recycle` 和 `pool_pre_ping`，数据库重启后旧连接报错。

**方案**：
```python
# server/app/database.py
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,    # 新增：1 小时回收空闲连接
    pool_pre_ping=True,   # 新增：使用前检测连接存活
)
```

- 修改文件：`server/app/database.py`

### 3.2 支付回调返回值修复

**现状**：`/notify` 端点忽略 `handle_payment_notify` 的返回值，签名验证失败也返回 "success"。

**方案**：注意端点同时支持 GET 和 POST（支付宝两种方式都可能用），需要分别处理：
```python
# server/app/routers/pay.py
@router.api_route("/notify", methods=["GET", "POST"])
async def pay_notify(request: Request, db=Depends(get_db)):
    if request.method == "POST":
        form_data = await request.form()
        data = dict(form_data)
    else:
        data = dict(request.query_params)
    success = await handle_payment_notify(db, data)
    return PlainTextResponse("success" if success else "failure")
```

- 修改文件：`server/app/routers/pay.py`

### 3.3 refresh-token 端点 Schema 化

**现状**：`/refresh-token` 接受 `data: dict`，无输入校验。

**方案**：
```python
# server/app/schemas/user.py
class RefreshTokenRequest(BaseModel):
    refreshToken: str = Field(..., min_length=1)

# server/app/routers/user.py
@router.post("/refresh-token")
async def refresh(data: RefreshTokenRequest, db=Depends(get_db)):
    result = await refresh_user_token(db, data.refreshToken)
    # ...
```

- 修改文件：`server/app/schemas/user.py`、`server/app/routers/user.py`

### 3.4 分页参数校验

**现状**：`page` 和 `pageSize` 接受负数、零、极大值。

**方案**：
```python
# server/app/routers/word_book.py
page: int = Query(1, ge=1, le=1000),
pageSize: int = Query(12, ge=1, le=100),
```

- 课程列表添加分页支持（limit + offset）
- 修改文件：`server/app/routers/word_book.py`、`server/app/services/course.py`

### 3.5 日志系统统一

**现状**：安全事件用 `print()` 输出，无法被日志系统捕获。

**方案**：全局替换为 `logging`，两个 FastAPI 应用统一配置。

当前 `ai/main.py` 已有 `lifespan` 配置了 logging。`app/main.py` 没有 `lifespan`，需要新增：
```python
# server/app/main.py — 新增 lifespan（当前不存在）
from contextlib import asynccontextmanager
import logging

@asynccontextmanager
async def lifespan(app):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    yield

app = FastAPI(title="English Server", version="0.1.0", lifespan=lifespan)
```

替换 print → logging：
- `middleware.py:100` → `logging.error(exc, exc_info=True)`
- `pay.py:117/129/153` → `logging.warning()`
- `socket.py:16` → `logging.info()`

- 修改文件：`server/app/main.py`、`server/app/middleware.py`、`server/app/services/pay.py`、`server/app/services/socket.py`

### 3.6 打卡并发竞态修复

**现状**：两个并发请求可同时通过"今日未打卡"检查，天数重复累加。

**方案**：在 UPDATE 的 WHERE 条件中加入日期检查：
```python
from sqlalchemy import update, func, or_

stmt = (
    update(User)
    .where(User.id == user_id)
    .where(
        or_(
            User.last_check_in_at.is_(None),
            func.date(User.last_check_in_at) != func.current_date(),
        )
    )
    .values(
        last_check_in_at=func.now(),
        day_number=User.day_number + 1,
    )
)
result = await db.execute(stmt)
if result.rowcount == 0:
    raise ValueError("今日已打卡")
await db.commit()
```

- 原子操作，不需要 `SELECT ... FOR UPDATE`
- 修改文件：`server/app/services/user.py`

### 3.7 Socket.IO userId 鉴权

**现状**：`userId` 直接从 query string 取，无验证。恶意网站可伪造。

**方案**：connect handler 中验证 JWT：
```python
async def connect(sid, environ):
    query = parse_qs(environ.get("QUERY_STRING", ""))
    token = query.get("token", [None])[0]
    if not token:
        raise ConnectionRefusedError("缺少认证 token")
    try:
        from app.services.auth import verify_token
        payload = verify_token(token)
        user_id = payload["userId"]
    except Exception:
        raise ConnectionRefusedError("认证失败")
    # ... 继续原有逻辑
```

- connect 时一次验证，后续事件处理无需重复校验
- 修改文件：`server/app/services/socket.py`

---

## 修改文件汇总

### 后端（server/）
| 文件 | 修改内容 |
|------|----------|
| `app/services/user.py` | bcrypt 密码哈希、头像鉴权+校验、打卡竞态修复 |
| `app/routers/user.py` | 限速、Schema 化、头像鉴权 |
| `app/routers/pay.py` | 支付回调返回值修复 |
| `app/main.py` | CORS 中间件、SlowAPIMiddleware、logging 配置 |
| `ai/main.py` | CORS 中间件 |
| `app/config.py` | cors_origins、alipay_return_url |
| `app/services/auth.py` | Token 时效 15 分钟 |
| `app/services/socket.py` | CORS 收紧、JWT 鉴权 |
| `app/services/pay.py` | 回调地址配置化、日志替换 |
| `app/database.py` | 连接池健康检查 |
| `app/middleware.py` | print → logging |
| `app/schemas/user.py` | RefreshTokenRequest |
| `app/routers/word_book.py` | 分页参数校验 |
| `app/services/course.py` | 课程列表分页 |
| `.env` | 新增配置项 |

### 前端（apps/web/src/）
| 文件 | 修改内容 |
|------|----------|
| `views/Course/Learn/index.vue` | XSS 消毒、错误处理 |
| `views/WordBook/index.vue` | XSS 消毒、错误处理 |
| `components/Search/index.vue` | XSS 消毒、事件监听清理 |
| `views/Chat/components/ChatArea.vue` | 自动滚动修复 |
| `views/Chat/components/RoleList.vue` | 错误处理 |
| `views/Chat/components/ConversationList.vue` | 错误处理 |
| `views/Course/index.vue` | 错误处理 |
| `views/Course/components/Pay.vue` | 错误处理 |
| `stores/user.ts` | 非空断言修复 |
| `stores/chat.ts` | 错误处理 |
| `apis/auth/index.ts` | Token 解析容错 |
| `router/index.ts` + 各子路由 | 路由守卫 |
| `views/Home/index.vue` | GSAP 清理、按需加载 |
| `views/Home/components/Hologram.vue` | Three.js 清理、按需加载 |
| `components/Login/index.vue` | 事件监听清理 |
| `components/Login/ModelViewer.vue` | Three.js 清理、按需加载 |

### 配置
| 文件 | 修改内容 |
|------|----------|
| `.gitignore` | 添加 .env 等规则 |
| `pyproject.toml` | 添加 bcrypt 依赖 |
