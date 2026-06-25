# 答辩前轻量优化设计（Pre-Launch Defense Polish）

> 日期：2026-06-25  
> 状态：**已实现**  
> 目标：**A 路线** — 本机 + FRP + 沙箱支付，评委能看通主流程  
> 前置：P0 QA（QA-03～05 等）已由用户人工验收通过

---

## 1. 背景

Launch Readiness 阶段 1～7 代码已完成；用户已完成 P0 演示验收。本期仅做 **P1 轻抛光**，不引入新业务能力。

## 2. 范围

| # | 项 | 改动 |
|---|-----|------|
| P1-1 | 支付 sync 轮询 | `query_alipay_trade` 对 SDK 返回 `bytes` 做 UTF-8 解码后再 `json.loads` |
| P1-2 | B 端用户列表 | 增加「角色」列：`admin` → 管理员 Tag，`user` → 用户 Tag |
| P1-3 | B 端订单详情 | 用户名/手机号可点击跳转 `/users/{userId}` |

## 3. 不在范围

- Refresh token 轮换、用户禁用、审计日志、ClickHouse
- 生产 HTTPS / 域名、FRP 文档（可后续补）
- SmokeUser 清理脚本

## 4. 验收

1. 沙箱支付后 `/pay/sync` 不再出现 `can only concatenate str (not "bytes") to str`
2. B 端用户列表可见角色 Tag
3. 订单详情点击用户进入用户详情页
4. `pnpm --filter @en/admin build` 通过
