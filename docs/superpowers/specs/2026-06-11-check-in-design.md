# 打卡功能设计

日期：2026-06-11

## 需求

用户每天手动打卡一次，打卡按钮在首页 Banner 区域，打卡成功有动画反馈。

## 后端

### 新增 API

`POST /api/v1/user/check-in`

- 鉴权：`Depends(get_current_user)`
- 逻辑：
  1. 根据 `user["userId"]` 查询用户记录
  2. 检查 `last_login_at` 是否是今天（比较日期部分）
  3. 如果今天已打卡：返回 `{ dayNumber: user.day_number }`，message 为 `"今日已打卡"`
  4. 如果今天未打卡：`day_number += 1`，更新 `last_login_at` 为当前时间，commit
  5. 返回 `{ dayNumber: user.day_number }`

### 字段复用

- `User.day_number` — 已有字段，打卡天数
- `User.last_login_at` — 已有字段，复用为"最后打卡时间"

不需要新增数据库字段或 migration。

### 文件改动

- `server/app/routers/user.py` — 新增 check-in 路由
- `server/app/services/user.py` — 新增 check_in 业务逻辑
- `server/app/schemas/user.py` — 可能需要新增响应 schema（或复用现有）

## 前端

### API 层

- `apps/web/src/apis/user/index.ts` — 新增 `checkIn()` 函数，POST `/user/check-in`

### Home Banner

- `apps/web/src/views/Home/index.vue` — 在"坚持5天打卡学习"区域下方加打卡按钮
  - 未登录：显示"登录后打卡"按钮，点击弹登录框
  - 已登录未打卡：显示"打卡"按钮（可点击）
  - 已打卡：显示"✅ 已打卡"（灰色不可点）

### 数据同步

- 打卡成功后调用 `userStore.updateUserWordNumber` 或新增 `updateDayNumber` 方法更新 Pinia store
- Profile 侧边栏自动响应（已有 `{{ userStore?.getUser?.dayNumber }}`）

### 动画效果

- 打卡成功后 Profile 的"打卡天数"数字有 +1 跳动动画
- Banner 区域按钮状态变化（打卡 → 已打卡）

## 状态判断

前端判断今天是否已打卡的方式：
- 打卡成功后在 Pinia store 中记录 `lastCheckInDate: string`（格式 `YYYY-MM-DD`）
- 页面加载时比较 `lastCheckInDate` 是否等于今天
- 或者直接调后端接口，后端返回是否已打卡

建议：前端记录 `lastCheckInDate`，避免每次刷新都请求后端。
