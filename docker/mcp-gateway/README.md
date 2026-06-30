# 已弃用：Node supergateway 方案

国内环境无法稳定拉取 `node:22-alpine`（Docker Hub 超时）。

**当前方案：** 复用 `english-server` 镜像内的 Python FastMCP sidecar，见 `server/external_mcp/` 与 `docs/external-mcp-setup.md`。
