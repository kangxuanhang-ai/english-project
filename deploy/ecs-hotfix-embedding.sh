#!/usr/bin/env bash
# ECS 热修复：知识库 embedding 模型无法从 HuggingFace 下载
# 在 ECS 上执行：bash /opt/english-project/ecs-hotfix-embedding.sh
set -euo pipefail

cd /opt/english-project
ENV_FILE="${ENV_FILE:-.env}"
HF_MIRROR="${HF_ENDPOINT:-https://hf-mirror.com}"

echo "==> 1/4 写入 HF_ENDPOINT 到 ${ENV_FILE}"
if grep -q '^HF_ENDPOINT=' "$ENV_FILE" 2>/dev/null; then
  sed -i "s|^HF_ENDPOINT=.*|HF_ENDPOINT=${HF_MIRROR}|" "$ENV_FILE"
else
  echo "HF_ENDPOINT=${HF_MIRROR}" >> "$ENV_FILE"
fi
grep HF_ENDPOINT "$ENV_FILE"

echo "==> 2/4 预下载 embedding 模型到 ai 容器（首次约 1～3 分钟）"
docker exec -e HF_ENDPOINT="${HF_MIRROR}" english-ai-1 uv run python -c "
import asyncio
from app.services.knowledge.embedding import embed_texts
async def main():
    v = await embed_texts(['test'])
    print('ok', len(v[0]))
asyncio.run(main())
"

echo "==> 3/4 重建 app / ai 容器以加载新环境变量"
if docker compose version >/dev/null 2>&1; then
  docker compose up -d --force-recreate app ai
else
  echo "WARN: docker compose 不可用，请手动重建 english-ai-1 / english-app-1"
fi

echo "==> 4/4 再次验证 embedding"
docker exec english-ai-1 uv run python -c "
import asyncio
from app.services.knowledge.embedding import embed_texts
async def main():
    v = await embed_texts(['test'])
    print('ok', len(v[0]))
asyncio.run(main())
"

echo "完成。请在浏览器新建对话后测试「vue是什么」或「你是谁」。"
