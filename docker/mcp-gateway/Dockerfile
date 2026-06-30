FROM node:22-alpine

RUN npm install -g supergateway @modelcontextprotocol/server-fetch

ENV MCP_PORT=8080

EXPOSE 8080

# supergateway 将 stdio MCP 转为 Streamable HTTP（/mcp）
CMD ["supergateway", "--stdio", "mcp-server-fetch", "--port", "8080", "--streamableHttpPath", "/mcp"]
