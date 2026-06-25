# B 端管理后台 UI 翻新设计

> 状态：**已评审** — 实现计划：[2026-06-25-admin-ui-redesign.md](../plans/2026-06-25-admin-ui-redesign.md)

## 概述

在现有 `apps/admin`（React 18 + Ant Design 5）功能完整的前提下，进行 **全站视觉翻新（D）**，并与 C 端 English 学习平台 **品牌统一（A）**。不改后端 API、路由或业务逻辑，仅调整主题、布局壳、公共组件与各页面排版。

**已确认决策：**

| 项 | 决策 |
|----|------|
| 品牌方向 | 与 C 端 Indigo 主色、暖白背景、大圆角气质一致 |
| 改动范围 | 全站：登录、布局壳、仪表盘、全部 List/Detail、数据监控 |
| 侧栏 | **浅色 Indigo 风格**（弃用默认 dark Sider） |
| 登录页左侧 | **纯渐变 + 文案**（不上 3D 模型） |
| 技术路线 | Ant Design `ConfigProvider theme` + 公共组件 + `admin-theme.css`（不引入 Tailwind） |

**已确认决策（评审补充）：**

| 项 | 决策 |
|----|------|
| `Placeholder.tsx` | **不在验收范围** — 未挂载路由，属早期占位；UI 翻新时 **删除该文件** |
| 侧栏宽度 | **240px 为最终值**（现有 220px 将被替换；折叠态 72px 不变） |

**不在本期：**

- 暗色模式切换
- 新功能或交互改版（仅视觉与布局）
- C 端样式迁移 / 3D 登录模型复用

---

## 设计 Token

与 C 端 `indigo-*`、`#faf9f6`、圆角 10–20px 对齐，映射到 Ant Design 5 `theme` 与 CSS 变量。

### 色彩

| Token | 值 | 用途 |
|-------|-----|------|
| `--admin-primary` | `#4338ca` | 主按钮、选中菜单、链接（= C 端 indigo-700） |
| `--admin-primary-hover` | `#6366f1` | 按钮 hover、图表主线 |
| `--admin-primary-light` | `#eef2ff` | 菜单选中背景、Tag 浅底 |
| `--admin-primary-muted` | `#c7d2fe` | 边框点缀、图表填充 |
| `--admin-bg-layout` | `#faf9f6` | 页面底色（= C 端 chat-main） |
| `--admin-bg-container` | `#ffffff` | Card、侧栏、顶栏 |
| `--admin-bg-subtle` | `#f4f4f5` | 表头、筛选区 secondary 背景 |
| `--admin-border` | `#e4e4e7` | Card 边框、分割线 |
| `--admin-text-primary` | `#18181b` | 标题、表格主文字 |
| `--admin-text-secondary` | `#71717a` | 描述、副标题 |
| `--admin-text-tertiary` | `#a1a1aa` | 占位、表格次要列 |
| `--admin-success` | `#059669` | 已支付、就绪 |
| `--admin-warning` | `#d97706` | 待处理、未支付 |
| `--admin-error` | `#dc2626` | 失败、错误日志 |
| `--admin-info` | `#0284c7` | 处理中 |

### 圆角与阴影

| Token | 值 |
|-------|-----|
| `borderRadiusSM` | `8px` — 按钮、输入框、Tag |
| `borderRadius` | `12px` — Card、Menu 项 |
| `borderRadiusLG` | `16px` — 登录表单 Card、大 StatCard |
| `boxShadowCard` | `0 1px 2px rgba(24,24,27,0.04), 0 4px 16px rgba(67,56,202,0.06)` |
| `boxShadowElevated` | `0 8px 32px rgba(67,56,202,0.12)` — 登录右栏 |

### 字体

```css
font-family: 'Plus Jakarta Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif;
```

- 从 Google Fonts 引入 Plus Jakarta Sans（400 / 600 / 700），与 C 端 chat 一致。
- 页面标题：`font-weight: 600`，`font-size: 20px`，`letter-spacing: -0.02em`。
- 卡片内 Stat 数字：`font-size: 28px`，`font-weight: 700`，主色或 `#18181b`。
- 表格/正文：`14px`；辅助说明：`13px`，secondary 色。

### Ant Design ConfigProvider 映射

```typescript
theme: {
  token: {
    colorPrimary: '#4338ca',
    colorLink: '#4338ca',
    colorBgLayout: '#faf9f6',
    colorBgContainer: '#ffffff',
    colorText: '#18181b',
    colorTextSecondary: '#71717a',
    colorBorder: '#e4e4e7',
    borderRadius: 12,
    borderRadiusLG: 16,
    fontFamily: "'Plus Jakarta Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif",
    controlHeight: 36,
    controlHeightLG: 40,
  },
  components: {
    Layout: { siderBg: '#ffffff', headerBg: '#ffffff', bodyBg: '#faf9f6' },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#eef2ff',
      itemSelectedColor: '#4338ca',
      itemHoverBg: '#f4f4f5',
      itemBorderRadius: 10,
      iconSize: 16,
    },
    Card: { paddingLG: 20 },
    Table: { headerBg: '#fafafa', headerColor: '#71717a', rowHoverBg: '#faf9ff' },
    Button: { primaryShadow: '0 2px 0 rgba(67,56,202,0.08)' },
  },
}
```

---

## 布局壳（AdminLayout）

### 结构

```
┌──────────────────────────────────────────────────────────────┐
│ Sider 240px          │ Header 56px                           │
│ (fixed, 白底)         ├──────────────────────────────────────┤
│                      │ Content (#faf9f6, padding 24px)       │
│ Logo                 │ max-width 1440px, margin auto         │
│ Nav Menu             │                                       │
│                      │                                       │
│ ─── (底) v0.1 可选    │                                       │
└──────────────────────────────────────────────────────────────┘
```

### 侧栏

- **宽度：** 240px（折叠态 72px，仅图标 + Tooltip，默认展开）。
- **背景：** `#ffffff`，右边框 `1px solid #e4e4e7`（不用 dark theme）。
- **Logo 区（高 64px）：**
  - 左：32×32 圆角 10px 方块，背景 `#4338ca`，白色粗体 **E**。
  - 右：主行 **English**，副行 **管理后台**（12px，secondary）。
  - 折叠时仅显示 E 方块，居中。
- **菜单项：**
  - 高度 44px，左右 padding 12px，图标与文字 gap 10px。
  - 默认：文字 `#52525b`，图标 `#71717a`。
  - 选中：`background #eef2ff`，文字/图标 `#4338ca`，左侧 **3px** Indigo 竖条（`border-inline-start`）。
  - Hover：未选中项 `#f4f4f5` 背景。
- **菜单顺序不变：** 仪表盘 / 知识库 / 用户 / 课程 / 订单 / 数据监控。

### 顶栏

- **高度 56px**，白底，底边框 `#e4e4e7`，`padding-inline: 24px`。
- **左侧：** Ant Design `Breadcrumb`（首页图标 + 当前模块 + 子页），末级 `#18181b` 加粗。
- **右侧：** 管理员区
  - 32px 圆形头像：Indigo 浅底 + 昵称首字；
  - 昵称 14px semibold；
  - 「退出」改为 `Button type="text"` + 图标，hover 浅灰底。

### 内容区

- 背景 `#faf9f6`，padding `24px`。
- 内层 `max-width: 1440px; margin: 0 auto`，宽屏不无限拉伸表格。

---

## 登录页

全屏 **左右分栏**，最小高度 100vh。

### 左侧（约 45% 宽，md 以下隐藏，表单居中占满）

- **背景渐变：**

  ```css
  background: linear-gradient(145deg, #312e81 0%, #4338ca 45%, #6366f1 100%);
  ```

- **装饰：** 2 个低透明度 radial 光晕（右上、左下，`rgba(255,255,255,0.08)`），避免 flat。
- **文案块（垂直居中，padding 48px）：**
  - 小标签：圆角 pill，半透明白底 — 「English Learning Platform」
  - 主标题（32px，白，700）：「运营管理后台」
  - 副标题（16px，`rgba(255,255,255,0.75)`）：「知识库 · 用户 · 课程 · 数据，一站管理」
  - 底部三条 bullet（14px，0.85  opacity）：仪表盘概览 / 知识库 RAG / 订单与监控

### 右侧（约 55%）

- 背景 `#faf9f6`，flex 居中。
- **表单 Card：** 宽 400px，`borderRadius 16px`，`boxShadowElevated`，padding 32px。
- 标题「管理后台登录」20px；副标题 secondary「使用管理员账号登录」。
- 输入框 `size="large"`，主按钮 `block` Indigo。
- 底部小字：「非管理员账号将无法进入」13px tertiary。

**逻辑不变：** `POST /api/v1/user/login`，校验 `role === 'admin'`。

---

## 公共组件

新建 `apps/admin/src/components/`，各页面统一引用。

### `PageShell`

| Prop | 说明 |
|------|------|
| `title` | 页面主标题 |
| `description?` | 一行灰色说明 |
| `extra?` | 右上操作区（Button 组） |
| `back?` | 详情页显示返回 + 标题 |
| `children` | 内容 |

- 标题区与内容区间距 20px。
- 详情页 `back` 使用 `Button type="text"` + `ArrowLeftOutlined`，点击 `navigate(-1)`。

### `FilterCard`

- 包裹筛选 `Space` / `Input.Search` / `Select` / `RangePicker`。
- Card 无 title，`padding: 16px 20px`，`marginBottom: 16px`。
- 内部控件垂直居中对齐，`gap: 12px`，允许 wrap。

### `DataCard`

- 包裹 `Table` 或 `Descriptions`。
- Card `bodyStyle padding: 0`（表格贴边）或 `padding: 20px`（Descriptions）。
- 表格场景：表头与 Card 顶边齐平，圆角由 Card 裁剪。

### `StatCard`

- 用于仪表盘指标。
- 布局：左上 40×40 圆角 10px 图标底（Indigo 浅底 + 主色图标），右上可选 tiny 趋势文案。
- 中间：Statistic 数字 28px bold。
- 底部：标题 14px secondary。
- Hover：`translateY(-2px)` + 阴影略加深（150ms ease），仅仪表盘使用。

### `EmptyHint`

- 统一空状态：Illustration 可选 Ant Design Empty + 自定义 `description`。
- 知识库无文档、订单无结果等复用。

---

## 页面级规范

### 仪表盘（`Dashboard.tsx`）

**第一行 — 4 个 StatCard（`gutter 16`）：**

| 卡片 | 图标 | 主数字 | 副文案 |
|------|------|--------|--------|
| 总用户 | TeamOutlined | userCount | — |
| 今日订单额 | PayCircleOutlined | todayRevenue | prefix ¥ |
| 知识库 | DatabaseOutlined | knowledgeDocCount | suffix「X 就绪」 |
| 今日 PV | EyeOutlined | todayPv | suffix「UV X」 |

**第二行 — 2 个图表 Card（各 `lg=12`）：**

- 标题 + 12px 说明「近 7 天趋势」。
- Line 图：`color: #4338ca`，`areaStyle fill: linear indigo 0.15→0`，`smooth: true`，`height: 240`。
- 空数据时 Card 内 Empty，不渲染空图表轴。

**第三行 — 5 个小 StatCard（`gutter 16`，每项 `flex:1` min）：**

今日新用户 / 课程总数 / 今日订单数 / 累计收入 / 近 7 天错误 — 不再挤在一个 Card 内。

**加载：** 第一行 StatCard skeleton + 图表 Card skeleton。

---

### 列表页（用户 / 课程 / 订单 / 知识库）

统一结构：

```
PageShell(title, description?)
  FilterCard(搜索 + 筛选 + 日期 + 主操作)
  DataCard(Table)
```

**表格：**

- `size="middle"`，`pagination.showTotal` 显示「共 N 条」。
- 行 hover `#faf9ff`；可点击行保留 `cursor: pointer`。
- 状态列 Tag 颜色与 `TRADE_STATUS_MAP` / `DOCUMENT_STATUS_MAP` 一致，圆角 pill。
- 金额列右对齐、semibold。
- 时间列使用已有 `formatDateTime`（北京时间）。

**知识库 List 额外：**

- 上传 Dragger 放入 FilterCard 下方独立 Card，虚线边框 Indigo，`padding: 24px`，图标 + 「拖拽或点击上传 txt / md / pdf / docx」。

**课程 List：**

- 「新建课程」按钮放 PageShell `extra`，`type="primary"`。

---

### 详情页（用户 / 订单 / 知识库）

```
PageShell(title=实体名, back)
  Row gutter 16
    Col lg=16: DataCard(Descriptions bordered column=2)
    Col lg=8:  次要 Card（用户订单列表 / 知识库 chunk 预览等）
```

- Descriptions `label` 宽度 120px，背景 `#fafafa`。
- 订单状态用大号 Tag 放在标题旁 `extra` 区域。

---

### 课程表单（`courses/Form.tsx`）

- PageShell + 单 Card 表单，`layout="vertical"`，`max-width: 640px`。
- 底部固定操作条：取消（default）+ 保存（primary），Card 内 `paddingBottom: 24px`。

---

### 数据监控（`analytics/Overview.tsx`）

- PageShell title「数据监控」+ description「埋点趋势与前端质量」。
- 顶部 `Segmented` + 天数切换放入 FilterCard。
- Stat 概览一行小 StatCard（PV/UV/错误数等，按现有 API 字段）。
- Tabs（流量 / 错误 / 性能）每个 Tab 内图表 + 表格用 DataCard 包裹。
- 图表配色与仪表盘 Line 一致。

---

### 知识库检索（`knowledge/Search.tsx`）

- PageShell + FilterCard（搜索框 + 检索按钮 primary）。
- 结果列表 Card：每条结果左侧 Indigo 竖条，相似度 Badge，正文 preview 最多 3 行 ellipsis。

---

## 交互与状态

| 场景 | 规范 |
|------|------|
| 页面加载 | 表格 `loading`；仪表盘 StatCard skeleton |
| 空数据 | `EmptyHint`，文案模块定制 |
| 操作成功 | 保持 Ant Design `message.success` |
| 删除确认 | `Popconfirm` 不变，按钮 danger |
| 路由切换 | 内容区可选 150ms opacity fade（CSS `.admin-content`） |

---

## 文件结构（实现时）

```
apps/admin/src/
├── styles/
│   └── admin-theme.css       # 变量、字体 import、内容区 fade
├── theme/
│   └── antd-theme.ts         # ConfigProvider token 导出
├── components/
│   ├── PageShell.tsx
│   ├── FilterCard.tsx
│   ├── DataCard.tsx
│   ├── StatCard.tsx
│   └── EmptyHint.tsx
├── layout/
│   └── AdminLayout.tsx       # 重写
├── views/
│   ├── Login.tsx             # 重写
│   ├── Dashboard.tsx         # 重写
│   └── …                     # 各 List/Detail 接入公共组件
│   # Placeholder.tsx         # 删除（无路由引用）
└── main.tsx                  # ConfigProvider + import theme css
```

---

## 验收标准

1. 登录页、侧栏、顶栏与 C 端 Header/Home **主色与圆角气质一致**（Indigo + 暖白）。
2. **全部已挂载路由的 view**（共 **12** 个，不含 `Login.tsx`、不含将删除的 `Placeholder.tsx`）均使用 `PageShell`。
3. 列表页筛选区均在 `FilterCard` 内，表格在 `DataCard` 内。
4. 仪表盘 StatCard 带图标与 hover，图表为 Indigo 色系。
5. `pnpm --filter @en/admin build` 通过，无 TypeScript 错误。
6. 1920 / 1280 / 768 宽度下布局不破裂；768 以下侧栏可折叠或 Ant Design 默认 drawer（沿用 Layout 响应式即可）。

---

## 参考

- C 端：`apps/web/src/layout/Header/index.vue`（Logo E + Indigo）
- C 端：`apps/web/src/views/Home/index.vue`（Indigo CTA、圆角 pill）
- C 端：`apps/web/src/assets/css/chat-theme.css`（`#faf9f6`、Plus Jakarta Sans）
- 现有 B 端功能 spec：`2026-06-24-admin-knowledge-base-design.md`
