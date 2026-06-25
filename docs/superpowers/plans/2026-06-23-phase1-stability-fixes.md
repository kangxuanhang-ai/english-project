# 阶段一：稳定性修复 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复安全漏洞、前端内存泄漏、后端稳定性问题，使项目可安全上线并参加校级答辩。

**Architecture:** 分三大批次实施 — 安全修复（后端为主）、前端稳定性（纯前端）、后端稳定性（纯后端）。每批次可独立验证。安全修复最先做，因为涉及密码和支付等核心功能。

**Tech Stack:** Python FastAPI, Vue 3, TypeScript, SQLAlchemy, bcrypt, slowapi, DOMPurify, Three.js, GSAP

**设计文档:** `docs/superpowers/specs/2026-06-23-phase1-stability-fixes-design.md`

---

## 批次一：安全修复

### Task 1: 添加 bcrypt 依赖

**Files:**
- Modify: `server/pyproject.toml`

- [ ] **Step 1: 在 pyproject.toml 的 dependencies 中添加 bcrypt**

```toml
dependencies = [
    # ... 现有依赖 ...
    "slowapi>=0.1.9",
    "bcrypt>=4.0",          # 新增
]
```

- [ ] **Step 2: 安装依赖**

Run: `cd server && uv sync`
Expected: bcrypt 安装成功，无报错

- [ ] **Step 3: 提交**

```bash
git add server/pyproject.toml server/uv.lock
git commit -m "deps: add bcrypt for password hashing"
```

---

### Task 2: 密码 bcrypt 哈希（注册 + 登录兼容迁移）

**Files:**
- Modify: `server/app/services/user.py`

- [ ] **Step 1: 在文件顶部添加 bcrypt 导入**

```python
import bcrypt
```

- [ ] **Step 2: 修改 register_user 函数 — 注册时用 bcrypt 哈希**

找到注册函数中存储密码的行（类似 `password=data["password"]`），改为：

```python
# 前端已 MD5 哈希，服务端再加一层 bcrypt
md5_hash = data["password"]
hashed = bcrypt.hashpw(md5_hash.encode(), bcrypt.gensalt()).decode()
# 存储 hashed 而非 data["password"]
```

- [ ] **Step 3: 修改 login_user 函数 — 登录时兼容 bcrypt 和旧 MD5**

找到登录函数中验证密码的行（类似 `if user.password != data["password"]`），改为：

```python
md5_hash = data["password"]

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
```

- [ ] **Step 4: 验证**

1. 用已有账号登录 → 应成功，密码自动升级为 bcrypt（数据库中以 `$2b$` 开头）
2. 用新密码注册 → 应成功，密码直接以 bcrypt 存储
3. 用升级后的账号再次登录 → 应成功，走 bcrypt 验证路径

- [ ] **Step 5: 提交**

```bash
git add server/app/services/user.py
git commit -m "feat: hash passwords with bcrypt, auto-migrate existing users on login"
```

---

### Task 3: .gitignore 补全

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 在 .gitignore 末尾添加**

```
# Environment files
.env
.env.*
server/.env
*.pem
*.key
```

- [ ] **Step 2: 确认 server/.env 未被追踪**

Run: `git ls-files server/.env`
Expected: 无输出（未被追踪）

- [ ] **Step 3: 提交**

```bash
git add .gitignore
git commit -m "chore: add .env and key files to .gitignore"
```

---

### Task 4: 配置 cors_origins 和 alipay_return_url

**Files:**
- Modify: `server/app/config.py`
- Modify: `server/.env`

- [ ] **Step 1: 在 Settings 类中添加两个新字段**

在 `server/app/config.py` 的 `Settings` 类中添加：

```python
# CORS
cors_origins: list[str] = Field(default=["http://localhost:8080"], alias="CORS_ORIGINS")

# 支付宝回调地址
alipay_return_url: str = Field(default="http://localhost:8080/courses/index", alias="ALIPAY_RETURN_URL")
```

- [ ] **Step 2: 在 server/.env 中添加对应配置**

```env
CORS_ORIGINS=http://localhost:8080
ALIPAY_RETURN_URL=http://localhost:8080/courses/index
```

- [ ] **Step 3: 验证配置加载**

Run: `cd server && uv run python -c "from app.config import settings; print(settings.cors_origins); print(settings.alipay_return_url)"`
Expected: 打印 `['http://localhost:8080']` 和 `http://localhost:8080/courses/index`

- [ ] **Step 4: 提交**

```bash
git add server/app/config.py server/.env
git commit -m "feat: add cors_origins and alipay_return_url config"
```

---

### Task 5: Socket.IO CORS 收紧

**Files:**
- Modify: `server/app/services/socket.py`

- [ ] **Step 1: 修改 Socket.IO 初始化**

找到：
```python
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
```

改为：
```python
from app.config import settings

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=settings.cors_origins)
```

- [ ] **Step 2: 验证**

启动服务端，确认无报错。从非 `http://localhost:8080` 的 origin 尝试 Socket.IO 连接应被拒绝。

- [ ] **Step 3: 提交**

```bash
git add server/app/services/socket.py
git commit -m "fix: restrict Socket.IO CORS to configured origins"
```

---

### Task 6: 头像上传鉴权 + 文件校验

**Files:**
- Modify: `server/app/routers/user.py`
- Modify: `server/app/services/user.py`

- [ ] **Step 1: 路由层添加鉴权**

找到 `upload-avatar` 路由（当前无鉴权），添加 `Depends(get_current_user)`：

```python
@router.post("/upload-avatar")
async def upload(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    """上传头像。添加鉴权，防止匿名上传"""
    try:
        result = await upload_avatar(file)
        return {"data": result, "code": 200, "message": "上传成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 2: 服务层添加文件校验**

在 `upload_avatar` 函数开头添加校验逻辑：

```python
import re

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

async def upload_avatar(file):
    # Content-type 校验
    if file.content_type not in ALLOWED_TYPES:
        raise ValueError("仅支持 JPG/PNG/WebP 格式")

    # 文件名校验（去掉路径分隔符）
    safe_name = re.sub(r'[^\w.\-]', '_', file.filename or "avatar.png")
    file_name = f"{int(time.time() * 1000)}-{safe_name}"

    # ... 后续原有逻辑，用 file_name 替代原来的文件名构造
```

- [ ] **Step 3: 验证**

1. 未登录时调用 `/api/v1/user/upload-avatar` → 应返回 401
2. 登录后上传 `.jpg`/`.png`/`.webp` → 应成功
3. 登录后上传 `.exe`/`.html` → 应返回 400 "仅支持 JPG/PNG/WebP 格式"

- [ ] **Step 4: 提交**

```bash
git add server/app/routers/user.py server/app/services/user.py
git commit -m "fix: add auth and file validation to avatar upload"
```

---

### Task 7: XSS 修复 — v-html 消毒

**Files:**
- Modify: `apps/web/src/views/Course/Learn/index.vue`
- Modify: `apps/web/src/views/WordBook/index.vue`
- Modify: `apps/web/src/components/Search/index.vue`

- [ ] **Step 1: 在 Course/Learn/index.vue 中添加 DOMPurify**

在 `<script setup>` 中添加导入：
```typescript
import DOMPurify from 'dompurify'
```

添加消毒函数：
```typescript
function sanitize(html: string): string {
    return DOMPurify.sanitize(html)
}
```

将模板中的 `v-html="currentWord?.definition"` 改为 `v-html="sanitize(currentWord?.definition ?? '')"`
将 `v-html="currentWord?.translation"` 改为 `v-html="sanitize(currentWord?.translation ?? '')"`

- [ ] **Step 2: 在 WordBook/index.vue 中添加 DOMPurify**

同上：导入 DOMPurify，添加 sanitize 函数，将 `v-html="item.translation"` 改为 `v-html="sanitize(item.translation)"`

- [ ] **Step 3: 在 Search/index.vue 中添加 DOMPurify**

同上：导入 DOMPurify，添加 sanitize 函数，将 `v-html="item.translation"` 改为 `v-html="sanitize(item.translation)"`

- [ ] **Step 4: 验证**

启动前端，访问词库页面和搜索功能，确认单词释义正常显示（DOMPurify 不会过滤正常的 HTML 标签如 `<b>`、`<i>`）

- [ ] **Step 5: 提交**

```bash
git add apps/web/src/views/Course/Learn/index.vue apps/web/src/views/WordBook/index.vue apps/web/src/components/Search/index.vue
git commit -m "fix: sanitize v-html with DOMPurify to prevent XSS"
```

---

### Task 8: 登录/注册限速

**Files:**
- Create: `server/app/rate_limit.py`
- Modify: `server/app/main.py`
- Modify: `server/app/routers/user.py`

- [ ] **Step 1: 创建共享 rate_limit 模块**

新建 `server/app/rate_limit.py`（复用 `ai/rate_limit.py` 的模式）：
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

- [ ] **Step 2: 在 app/main.py 中配置 slowapi**

在文件顶部添加导入：
```python
from app.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
```

在 `app = FastAPI(...)` 之后添加：
```python
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

- [ ] **Step 3: 在 user.py 路由中添加限速装饰器**

在 `server/app/routers/user.py` 中导入共享实例：
```python
from app.rate_limit import limiter
```

给 login 路由添加装饰器（注意顺序：limiter 在 router 上方）：
```python
@limiter.limit("5/minute")
@router.post("/login")
async def login(...):
```

给 register 路由添加装饰器：
```python
@limiter.limit("3/minute")
@router.post("/register")
async def register(...):
```

- [ ] **Step 4: 验证**

快速连续发送 6 次登录请求 → 第 6 次应返回 429 Too Many Requests

- [ ] **Step 5: 提交**

```bash
git add server/app/rate_limit.py server/app/main.py server/app/routers/user.py
git commit -m "feat: add rate limiting to login and register endpoints"
```

---

### Task 9: JWT 密钥 + Token 时效

**Files:**
- Modify: `server/app/services/auth.py`
- Modify: `server/.env`

- [ ] **Step 1: 生成新的 SECRET_KEY**

Run: `cd server && uv run python -c "import secrets; print(secrets.token_hex(32))"`
Expected: 输出类似 `a1b2c3d4e5f6...` 的 64 字符十六进制字符串

- [ ] **Step 2: 更新 server/.env 中的 SECRET_KEY**

将 `SECRET_KEY=` 后面替换为上一步生成的字符串

- [ ] **Step 3: 修改 Token 时效**

在 `server/app/services/auth.py` 中找到 `access_token_expires` 的定义（当前为 `timedelta(seconds=10)`），改为：

```python
access_token_expires = timedelta(minutes=15)
```

- [ ] **Step 4: 验证**

1. 登录获取 token → 解码 token 确认 `exp` 字段为 15 分钟后
2. 前端正常使用 → 确认 token 刷新流程正常工作

- [ ] **Step 5: 提交**

```bash
git add server/.env server/app/services/auth.py
git commit -m "fix: strengthen SECRET_KEY, extend access token to 15 minutes"
```

---

### Task 10: 支付宝回调地址配置化

**Files:**
- Modify: `server/app/services/pay.py`

- [ ] **Step 1: 找到硬编码的 return_url**

搜索 `localhost:8080/courses/index`，找到类似：
```python
request.return_url = "http://localhost:8080/courses/index"
```

改为：
```python
request.return_url = settings.alipay_return_url
```

确认文件顶部有 `from app.config import settings` 导入（如果没有则添加）。

- [ ] **Step 2: 验证**

配置文件已在 Task 4 中更新。确认 `settings.alipay_return_url` 能正确读取。

- [ ] **Step 3: 提交**

```bash
git add server/app/services/pay.py
git commit -m "fix: read Alipay return URL from config instead of hardcoded"
```

---

### Task 11: CORS 中间件

**Files:**
- Modify: `server/app/main.py`
- Modify: `server/ai/main.py`

- [ ] **Step 1: 在 app/main.py 中添加 CORS 中间件**

在 `app = FastAPI(...)` 之后添加：
```python
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 2: 在 ai/main.py 中添加 CORS 中间件**

在 `ai_app = FastAPI(...)` 之后添加：
```python
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

ai_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 3: 验证**

1. 从 `http://localhost:8080` 发起请求 → 应正常返回
2. 从其他 origin 发起请求 → 应被 CORS 拦截

- [ ] **Step 4: 提交**

```bash
git add server/app/main.py server/ai/main.py
git commit -m "feat: add CORS middleware to both FastAPI apps"
```

---

---

## 批次二：前端稳定性修复

### Task 12: Three.js 资源清理 — Hologram.vue

**Files:**
- Modify: `apps/web/src/views/Home/components/Hologram.vue`

- [ ] **Step 1: 找到 initThree 函数中的动画循环**

找到 `requestAnimationFrame` 调用处，将返回值保存到变量：
```typescript
let animationId: number

function animate() {
    animationId = requestAnimationFrame(animate)
    // ... 原有渲染逻辑
}
```

- [ ] **Step 2: 添加 onUnmounted 清理**

在 `<script setup>` 中添加：
```typescript
import { onUnmounted } from 'vue'

let renderer: THREE.WebGLRenderer | null = null
let controls: OrbitControls | null = null
let scene: THREE.Scene | null = null

onUnmounted(() => {
    if (animationId) cancelAnimationFrame(animationId)
    if (controls) controls.dispose()
    if (renderer) {
        renderer.dispose()
        renderer.domElement.remove()
    }
    if (scene) {
        scene.traverse((obj) => {
            if ((obj as any).isMesh) {
                const mesh = obj as THREE.Mesh
                mesh.geometry.dispose()
                if (Array.isArray(mesh.material)) {
                    mesh.material.forEach(m => m.dispose())
                } else {
                    mesh.material.dispose()
                }
            }
        })
    }
})
```

注意：需要将 `renderer`、`controls`、`scene` 的声明从 `initThree` 内部提升到 `<script setup>` 顶层，以便 `onUnmounted` 能访问。

- [ ] **Step 3: 验证**

1. 访问首页 → Hologram 正常显示
2. 导航到其他页面 → 浏览器控制台无 Three.js 相关警告
3. 多次进出首页 → WebGL 上下文数量不持续增长（Chrome DevTools → Memory）

- [ ] **Step 4: 提交**

```bash
git add apps/web/src/views/Home/components/Hologram.vue
git commit -m "fix: cleanup Three.js resources on Hologram unmount"
```

---

### Task 13: Three.js 资源清理 — ModelViewer.vue

**Files:**
- Modify: `apps/web/src/components/Login/ModelViewer.vue`

- [ ] **Step 1: 与 Task 12 相同的模式**

将 `renderer`、`controls`、`scene`、`animationId` 提升到顶层变量，添加 `onUnmounted` 清理。

```typescript
import { onUnmounted } from 'vue'

let animationId: number
let renderer: THREE.WebGLRenderer | null = null
let controls: OrbitControls | null = null
let scene: THREE.Scene | null = null

onUnmounted(() => {
    if (animationId) cancelAnimationFrame(animationId)
    if (controls) controls.dispose()
    if (renderer) {
        renderer.dispose()
        renderer.domElement.remove()
    }
    if (scene) {
        scene.traverse((obj) => {
            if ((obj as any).isMesh) {
                const mesh = obj as THREE.Mesh
                mesh.geometry.dispose()
                if (Array.isArray(mesh.material)) {
                    mesh.material.forEach(m => m.dispose())
                } else {
                    mesh.material.dispose()
                }
            }
        })
    }
})
```

- [ ] **Step 2: 验证**

1. 打开登录弹窗 → 3D 模型正常显示
2. 关闭弹窗 → WebGL 资源释放

- [ ] **Step 3: 提交**

```bash
git add apps/web/src/components/Login/ModelViewer.vue
git commit -m "fix: cleanup Three.js resources on ModelViewer unmount"
```

---

### Task 14: 事件监听器清理

**Files:**
- Modify: `apps/web/src/components/Login/index.vue`
- Modify: `apps/web/src/components/Search/index.vue`

- [ ] **Step 1: 修复 Login/index.vue**

找到 `window.addEventListener('keydown', ...)` 调用。如果是直接在 `<script setup>` 顶层调用的，改为：

```typescript
import { onMounted, onUnmounted } from 'vue'

function onKeydown(e: KeyboardEvent) {
    // ... 原有逻辑
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
```

- [ ] **Step 2: 修复 Search/index.vue**

同上模式：将 `window.addEventListener` 移入 `onMounted`，添加 `onUnmounted` 移除。

- [ ] **Step 3: 验证**

1. 打开登录弹窗 → 按 Escape 可关闭
2. 关闭后再打开 → 按 Escape 仍可关闭（无重复监听）
3. 搜索组件同理

- [ ] **Step 4: 提交**

```bash
git add apps/web/src/components/Login/index.vue apps/web/src/components/Search/index.vue
git commit -m "fix: cleanup keyboard event listeners on unmount"
```

---

### Task 15: GSAP ScrollTrigger 清理

**Files:**
- Modify: `apps/web/src/views/Home/index.vue`

- [ ] **Step 1: 在 <script setup> 中添加 onUnmounted**

```typescript
import { onUnmounted } from 'vue'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

onUnmounted(() => {
    ScrollTrigger.getAll().forEach(t => t.kill())
})
```

- [ ] **Step 2: 验证**

1. 访问首页 → 滚动动画正常
2. 导航到聊天页 → 再回首页 → 滚动动画正常（无重复触发）
3. 多次进出首页 → 无内存泄漏

- [ ] **Step 3: 提交**

```bash
git add apps/web/src/views/Home/index.vue
git commit -m "fix: kill all ScrollTrigger instances on Home unmount"
```

---

### Task 16: Store 非空断言修复

**Files:**
- Modify: `apps/web/src/stores/user.ts`

- [ ] **Step 1: 修复所有 `user.value!` 调用**

逐个修改以下方法，添加 null 检查：

```typescript
const updateToken = (newToken: Token) => {
    if (!user.value) return
    user.value.token = newToken
}

const updateUserWordNumber = (wordNumber: number) => {
    if (!user.value) return
    user.value.wordNumber = wordNumber
}

const updateUser = (params: UserUpdate) => {
    if (!user.value) return
    user.value.name = params.name
    user.value.email = params.email
    user.value.address = params.address
    user.value.avatar = params.avatar
    user.value.bio = params.bio
    user.value.isTimingTask = params.isTimingTask
    user.value.timingTaskTime = params.timingTaskTime
}

const getUpdateUserInfo = computed<UserUpdate>(() => {
    if (!user.value) {
        return { name: '', email: '', address: '', avatar: '', bio: '', isTimingTask: false, timingTaskTime: '' }
    }
    return {
        name: user.value.name,
        email: user.value.email,
        address: user.value.address,
        avatar: user.value.avatar,
        bio: user.value.bio,
        isTimingTask: user.value.isTimingTask,
        timingTaskTime: user.value.timingTaskTime,
    }
})
```

- [ ] **Step 2: 验证**

1. 登录 → 正常使用
2. 退出登录 → 再访问设置页面 → 不应崩溃（应重定向到首页）

- [ ] **Step 3: 提交**

```bash
git add apps/web/src/stores/user.ts
git commit -m "fix: add null checks to user store methods to prevent TypeError"
```

---

### Task 17: 路由守卫

**Files:**
- Modify: `apps/web/src/router/index.ts`
- Modify: 各子路由文件（`chat/index.ts`、`setting/index.ts`、`course/index.ts`）

- [ ] **Step 1: 给需要登录的路由添加 meta.requiresAuth**

在 `apps/web/src/router/chat/index.ts` 中：
```typescript
{
    path: '/chat/:role/:conversationId?',
    component: () => import('@/views/Chat/index.vue'),
    meta: { requiresAuth: true }
}
```

在 `apps/web/src/router/setting/index.ts` 中：
```typescript
{
    path: '/setting/index',
    component: () => import('@/views/Setting/index.vue'),
    meta: { requiresAuth: true }
}
```

在 `apps/web/src/router/course/index.ts` 中，学习路由需要鉴权：
```typescript
{
    path: '/courses/learn/:courseId/:title',
    component: () => import('@/views/Course/Learn/index.vue'),
    meta: { requiresAuth: true }
}
// 课程列表不需要登录，可浏览
{
    path: '/courses/index',
    component: () => import('@/views/Course/index.vue'),
}
```

- [ ] **Step 2: 在 router/index.ts 中添加 beforeEach 守卫**

```typescript
import { useUserStore } from '@/stores/user'

router.beforeEach((to) => {
    if (to.meta.requiresAuth) {
        const userStore = useUserStore()
        if (!userStore.getAccessToken) {
            return { path: '/' }
        }
    }
})
```

- [ ] **Step 3: 验证**

1. 未登录时访问 `/chat/normal` → 应重定向到首页
2. 未登录时访问 `/courses/index` → 应正常显示（可浏览）
3. 登录后访问 `/chat/normal` → 应正常显示

- [ ] **Step 4: 提交**

```bash
git add apps/web/src/router/
git commit -m "feat: add route guards for auth-required pages"
```

---

### Task 18: 错误处理补全 — 聊天组件

**Files:**
- Modify: `apps/web/src/views/Chat/components/RoleList.vue`
- Modify: `apps/web/src/views/Chat/components/ConversationList.vue`
- Modify: `apps/web/src/stores/chat.ts`

- [ ] **Step 1: RoleList.vue — getChatMode 添加 try/catch**

```typescript
import { ElMessage } from 'element-plus'

const getChatMode = async () => {
    try {
        const res = await getChatModes()
        // ... 原有赋值逻辑
    } catch (error) {
        ElMessage.error('加载角色列表失败')
    }
}
```

- [ ] **Step 2: ConversationList.vue — handleCreate 添加 try/catch**

```typescript
const handleCreate = async () => {
    try {
        await chatStore.createConversation(chatStore.activeRole)
    } catch (error) {
        ElMessage.error('创建对话失败')
    }
}
```

- [ ] **Step 3: ConversationList.vue — deleteConversation 添加 try/catch**

```typescript
const deleteConversation = async (id: string) => {
    try {
        await chatStore.deleteConversation(id)
    } catch (error) {
        ElMessage.error('删除对话失败')
    }
}
```

- [ ] **Step 4: stores/chat.ts — 添加错误处理**

给 `setRole`、`createConversation`、`deleteConversation` 添加 try/catch + ElMessage.error。

- [ ] **Step 5: 提交**

```bash
git add apps/web/src/views/Chat/components/RoleList.vue apps/web/src/views/Chat/components/ConversationList.vue apps/web/src/stores/chat.ts
git commit -m "fix: add error handling to chat components and store"
```

---

### Task 19: 错误处理补全 — 课程和词库页面

**Files:**
- Modify: `apps/web/src/views/Course/index.vue`
- Modify: `apps/web/src/views/Course/components/Pay.vue`
- Modify: `apps/web/src/views/Course/Learn/index.vue`
- Modify: `apps/web/src/views/WordBook/index.vue`

- [ ] **Step 1: Course/index.vue — getList 添加 try/catch/finally**

```typescript
import { ElMessage } from 'element-plus'

const getList = async () => {
    try {
        isLoading.value = true
        const res = await getCourseList()
        list.value = res.data
    } catch (error) {
        ElMessage.error('加载课程列表失败')
    } finally {
        isLoading.value = false
    }
}
```

- [ ] **Step 2: Pay.vue — onConfirm 添加 try/catch/finally**

```typescript
const onConfirm = async () => {
    try {
        isPay.value = true
        const res = await createPay({ courseId: props.courseId })
        window.open(res.data.payUrl, '_blank')
    } catch (error) {
        ElMessage.error('创建支付订单失败')
    } finally {
        isPay.value = false
    }
}
```

- [ ] **Step 3: Learn/index.vue — getWordListData 添加 try/catch/finally**

```typescript
const getWordListData = async () => {
    try {
        isLoading.value = true
        const res = await getWordList(route.params.courseId as string)
        wordList.value = res.data
    } catch (error) {
        ElMessage.error('加载单词列表失败')
    } finally {
        isLoading.value = false
    }
}
```

- [ ] **Step 4: WordBook/index.vue — getList 添加 try/catch/finally**

注意：实际代码用 `query.value` 包含所有查询字段，需按实际结构调整：

```typescript
const getList = async () => {
    try {
        isLoading.value = true
        const res = await getWordBookList(query.value)
        list.value = res.data
    } catch (error) {
        ElMessage.error('加载词库列表失败')
    } finally {
        isLoading.value = false
    }
}
```

- [ ] **Step 5: 提交**

```bash
git add apps/web/src/views/Course/index.vue apps/web/src/views/Course/components/Pay.vue apps/web/src/views/Course/Learn/index.vue apps/web/src/views/WordBook/index.vue
git commit -m "fix: add error handling to course and wordbook pages"
```

---

### Task 20: 聊天自动滚动修复

**Files:**
- Modify: `apps/web/src/views/Chat/components/ChatArea.vue`

- [ ] **Step 1: 修改 scrollToBottom 函数**

找到当前的 `scrollToBottom` 函数（约第 86-93 行），改为：

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

- [ ] **Step 2: 在 sendMessage 中添加强制滚动**

找到 `list.value.push({ role: 'human', ... })` 那行（约第 179 行），在其后添加：

```typescript
nextTick(() => scrollToBottom(true))
```

- [ ] **Step 3: 确认 SSE 回调中的 scrollToBottom 调用不变**

SSE 回调中的 `scrollToBottom()` 调用（无参数）保持不变，它们会自动使用 `force = false`。

- [ ] **Step 4: 验证**

1. 在聊天中往上滚动看历史消息
2. 发送新消息 → 应自动滚动到底部
3. AI 流式回复时 → 如果在底部附近自动跟随，如果往上滚动则不打断

- [ ] **Step 5: 提交**

```bash
git add apps/web/src/views/Chat/components/ChatArea.vue
git commit -m "fix: force scroll to bottom on message send"
```

---

### Task 21: JWT Token 解析容错

**Files:**
- Modify: `apps/web/src/apis/auth/index.ts`

- [ ] **Step 1: 修改 ensureValidToken 的 catch 块**

找到 `ensureValidToken` 函数中的 try/catch（约第 37-50 行），将 catch 块改为：

```typescript
} catch {
    return null  // 原来是 return token，会导致损坏 token 的无限 401 循环
}
```

- [ ] **Step 2: 验证**

1. 正常登录 → token 刷新正常工作
2. 手动在 localStorage 中修改 token 为一个无效值 → 应返回 null，触发重新登录

- [ ] **Step 3: 提交**

```bash
git add apps/web/src/apis/auth/index.ts
git commit -m "fix: return null on JWT parse failure to prevent infinite 401 loop"
```

---

### Task 22: 重型库按需加载

**Files:**
- Modify: `apps/web/src/views/Home/components/Hologram.vue`
- Modify: `apps/web/src/components/Login/ModelViewer.vue`
- Modify: `apps/web/src/views/Home/index.vue`

- [ ] **Step 1: Hologram.vue — Three.js 动态导入**

将顶部的静态导入：
```typescript
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
```

改为在 `onMounted` 中动态导入：
```typescript
const isLoaded = ref(false)

onMounted(async () => {
    const THREE = await import('three')
    const { OrbitControls } = await import('three/addons/controls/OrbitControls.js')
    const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js')
    // ... 用 THREE、OrbitControls、GLTFLoader 初始化场景
    isLoaded.value = true
})
```

模板中 canvas 添加 `v-if="isLoaded"`，加载完成前可显示一个 loading 占位。

- [ ] **Step 2: ModelViewer.vue — 同上模式**

同 Hologram.vue，将 Three.js 导入改为动态 import。

- [ ] **Step 3: Home/index.vue — GSAP 动态导入**

将顶部的静态导入：
```typescript
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
```

改为在 `onMounted` 中动态导入：
```typescript
onMounted(async () => {
    const gsap = (await import('gsap')).default
    const { ScrollTrigger } = await import('gsap/ScrollTrigger')
    gsap.registerPlugin(ScrollTrigger)
    // ... 原有动画初始化逻辑
})
```

注意：`onUnmounted` 中的 `ScrollTrigger.getAll()` 也需要在 `onMounted` 内部定义，或通过闭包引用。

- [ ] **Step 4: 验证**

1. 首次加载首页 → Three.js 和 GSAP 应在 Network 面板中显示为延迟加载
2. 直接访问 `/chat` → 不应加载 Three.js 和 GSAP 的 chunk
3. 3D 全息动画和滚动动画正常工作

- [ ] **Step 5: 提交**

```bash
git add apps/web/src/views/Home/components/Hologram.vue apps/web/src/components/Login/ModelViewer.vue apps/web/src/views/Home/index.vue
git commit -m "perf: lazy load Three.js and GSAP with dynamic imports"
```

---

---

## 批次三：后端稳定性修复

### Task 23: 数据库连接池健康检查

**Files:**
- Modify: `server/app/database.py`

- [ ] **Step 1: 修改 create_async_engine 调用**

找到当前的引擎创建代码（约第 7-12 行），添加两个参数：

```python
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,    # 新增：1 小时回收空闲连接
    pool_pre_ping=True,   # 新增：使用前检测连接存活
)
```

- [ ] **Step 2: 验证**

启动服务端，确认无报错。如果有数据库连接，确认正常工作。

- [ ] **Step 3: 提交**

```bash
git add server/app/database.py
git commit -m "fix: add pool_recycle and pool_pre_ping for connection health checks"
```

---

### Task 24: 支付回调返回值修复

**Files:**
- Modify: `server/app/routers/pay.py`

- [ ] **Step 1: 修改 notify 端点**

找到 `/notify` 路由（约第 27-37 行），当前代码类似：
```python
await handle_payment_notify(db, data)
return PlainTextResponse("success")
```

改为：
```python
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

- [ ] **Step 2: 验证**

确认 `handle_payment_notify` 返回 `bool` 类型。

- [ ] **Step 3: 提交**

```bash
git add server/app/routers/pay.py
git commit -m "fix: return payment notify result instead of always 'success'"
```

---

### Task 25: refresh-token 端点 Schema 化

**Files:**
- Modify: `server/app/schemas/user.py`
- Modify: `server/app/routers/user.py`

- [ ] **Step 1: 在 schemas/user.py 中添加 RefreshTokenRequest**

```python
from pydantic import BaseModel, Field

class RefreshTokenRequest(BaseModel):
    refreshToken: str = Field(..., min_length=1)
```

- [ ] **Step 2: 修改 refresh-token 路由**

找到 `/refresh-token` 跟由（当前签名为 `data: dict`），改为：

```python
@router.post("/refresh-token")
async def refresh(data: RefreshTokenRequest, db=Depends(get_db)):
    try:
        result = await refresh_user_token(db, data.refreshToken)
        return {"data": result, "code": 200, "message": "刷新成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 3: 验证**

1. 发送空 body → 应返回 422 验证错误
2. 发送正确的 refreshToken → 应返回新 token

- [ ] **Step 4: 提交**

```bash
git add server/app/schemas/user.py server/app/routers/user.py
git commit -m "fix: add schema validation to refresh-token endpoint"
```

---

### Task 26: 分页参数校验

**Files:**
- Modify: `server/app/routers/word_book.py`
- Modify: `server/app/services/course.py`

- [ ] **Step 1: word_book.py — 添加分页参数约束**

找到 `page` 和 `pageSize` 参数定义（约第 12-13 行），改为：

```python
page: int = Query(1, ge=1, le=1000),
pageSize: int = Query(12, ge=1, le=100),
```

- [ ] **Step 2: course.py — 课程列表添加分页**

找到 `get_course_list` 函数（无分页参数），添加分页支持：

```python
async def get_course_list(db: AsyncSession, page: int = 1, page_size: int = 12) -> dict:
    offset = (page - 1) * page_size
    result = await db.execute(select(Course).offset(offset).limit(page_size))
    courses = result.scalars().all()
    # 获取总数
    count_result = await db.execute(select(func.count(Course.id)))
    total = count_result.scalar()
    return {"list": courses, "total": total}
```

对应的路由也需要添加 `page` 和 `pageSize` 查询参数。

- [ ] **Step 3: 验证**

1. `GET /api/v1/word-book?page=-1` → 应返回 422
2. `GET /api/v1/word-book?pageSize=99999` → 应返回 422
3. `GET /api/v1/word-book?page=1&pageSize=12` → 应正常返回

- [ ] **Step 4: 提交**

```bash
git add server/app/routers/word_book.py server/app/services/course.py
git commit -m "fix: validate pagination parameters, add pagination to course list"
```

---

### Task 27: 日志系统统一

**Files:**
- Modify: `server/app/main.py`
- Modify: `server/app/middleware.py`
- Modify: `server/app/services/pay.py`
- Modify: `server/app/services/socket.py`

- [ ] **Step 1: app/main.py — 新增 lifespan 和 logging 配置**

在 `app/main.py` 顶部添加导入：
```python
from contextlib import asynccontextmanager
import logging
```

添加 lifespan 函数（当前不存在）：
```python
@asynccontextmanager
async def lifespan(app):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    yield
```

修改 FastAPI 初始化：
```python
app = FastAPI(title="English Server", version="0.1.0", lifespan=lifespan)
```

- [ ] **Step 2: middleware.py — print 替换为 logging**

找到第 100 行 `print(f"Unhandled exception: {exc}")`，改为：
```python
logging.error(f"Unhandled exception: {exc}", exc_info=True)
```

在文件顶部添加 `import logging`。

- [ ] **Step 3: pay.py — print 替换为 logging**

找到以下三处 print 调用，替换为 logging：
- `print(f"Signature verification failed: {e}")` → `logging.warning(f"Signature verification failed: {e}")`
- `print("Alipay signature verification failed")` → `logging.warning("Alipay signature verification failed")`
- `print(f"Failed to parse payment body: {e}")` → `logging.warning(f"Failed to parse payment body: {e}")`

在文件顶部添加 `import logging`。

- [ ] **Step 4: socket.py — print 替换为 logging**

找到 `print(f"Socket.IO: user_{user_id} connected")`，改为：
```python
logging.info(f"Socket.IO: user_{user_id} connected")
```

在文件顶部添加 `import logging`。

- [ ] **Step 5: 验证**

启动服务端，触发各种操作，确认日志格式正确输出。

- [ ] **Step 6: 提交**

```bash
git add server/app/main.py server/app/middleware.py server/app/services/pay.py server/app/services/socket.py
git commit -m "fix: replace print with structured logging across backend"
```

---

### Task 28: 打卡并发竞态修复

**Files:**
- Modify: `server/app/services/user.py`

- [ ] **Step 1: 重写 check_in 函数**

找到 `check_in` 函数（约第 190 行），将其核心逻辑替换为原子 UPDATE + returning：

```python
from sqlalchemy import update, func, or_

async def check_in(db: AsyncSession, user_id: str) -> dict:
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
        .returning(User.day_number)
    )
    result = await db.execute(stmt)
    day_number = result.scalar_one_or_none()
    if day_number is None:
        raise ValueError("今日已打卡")
    await db.commit()
    return {"dayNumber": day_number}
```

- [ ] **Step 2: 验证**

1. 首次打卡 → 应成功，day_number 为 1
2. 同一天再次打卡 → 应返回 400 "今日已打卡"
3. 新用户（last_check_in_at 为 NULL）首次打卡 → 应成功

- [ ] **Step 3: 提交**

```bash
git add server/app/services/user.py
git commit -m "fix: use atomic UPDATE to prevent check-in race condition"
```

---

### Task 29: Socket.IO userId 鉴权

**Files:**
- Modify: `server/app/services/socket.py`

- [ ] **Step 1: 修改 connect handler**

找到 `connect` 函数（约第 12-14 行），当前代码类似：
```python
async def connect(sid, environ):
    query = parse_qs(environ.get("QUERY_STRING", ""))
    user_id = query.get("userId", [None])[0]
```

改为：
```python
from urllib.parse import parse_qs
from app.services.auth import verify_token

async def connect(sid, environ):
    query = parse_qs(environ.get("QUERY_STRING", ""))
    token = query.get("token", [None])[0]
    if not token:
        raise ConnectionRefusedError("缺少认证 token")
    try:
        payload = verify_token(token)
        user_id = payload["userId"]
    except Exception:
        raise ConnectionRefusedError("认证失败")
    # ... 继续原有逻辑（join room 等）
```

- [ ] **Step 2: 前端 Socket.IO 连接改为传 token**

在 `apps/web/src/hooks/useSocket.ts` 中，找到 Socket.IO 连接代码，将 `userId` 参数改为 `token`：

```typescript
const userStore = useUserStore()
socket = io(socketUrl, {
    query: {
        token: userStore.getAccessToken
    }
})
```

- [ ] **Step 3: 验证**

1. 登录后 → Socket.IO 连接成功
2. 未登录或 token 过期 → Socket.IO 连接被拒绝
3. 支付成功消息仍能通过 Socket.IO 正常接收

- [ ] **Step 4: 提交**

```bash
git add server/app/services/socket.py apps/web/src/hooks/useSocket.ts
git commit -m "fix: verify JWT token in Socket.IO connect handler"
```

---

## 完成

所有 29 个 Task 完成后，运行完整验证：

```bash
# 后端
cd server && uv run python -m uvicorn app.main:socket_app --port 3000
cd server && uv run python -m uvicorn ai.main:ai_app --port 3001

# 前端
cd apps/web && pnpm dev
```

验证清单：
- [ ] 注册新账号 → 密码以 bcrypt 存储
- [ ] 登录旧账号 → 自动迁移为 bcrypt
- [ ] 登录/注册限速生效
- [ ] 头像上传需要登录
- [ ] 词库/搜索页面 XSS 消毒正常
- [ ] 聊天自动滚动正常
- [ ] 路由守卫生效
- [ ] 支付回调返回正确结果
- [ ] 打卡竞态修复
- [ ] Socket.IO 鉴权生效
- [ ] 控制台无 Three.js/GSAP 内存泄漏警告
- [ ] 日志格式统一
