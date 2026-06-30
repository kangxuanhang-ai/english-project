# 主 API + AI 服务共用镜像，启动命令由 compose 区分
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.6.15 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --frozen --no-dev

COPY server/ ./

# 构建阶段预下载 embedding 模型，避免线上容器首次调用 knowledge_search 时访问 HuggingFace 失败
ENV HF_ENDPOINT=https://hf-mirror.com
RUN uv run python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-zh-v1.5')"

COPY docker/server/entrypoint-app.sh /entrypoint-app.sh
COPY docker/server/bootstrap.py /app/docker/server/bootstrap.py
RUN chmod +x /entrypoint-app.sh

EXPOSE 3000 3001

ENTRYPOINT ["/entrypoint-app.sh"]
CMD ["uv", "run", "python", "-m", "uvicorn", "app.main:socket_app", "--host", "0.0.0.0", "--port", "3000"]
