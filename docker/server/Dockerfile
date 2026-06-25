# 主 API + AI 服务共用镜像，启动命令由 compose 区分
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --frozen --no-dev

COPY server/ ./

COPY docker/server/entrypoint-app.sh /entrypoint-app.sh
COPY docker/server/bootstrap.py /app/docker/server/bootstrap.py
RUN chmod +x /entrypoint-app.sh

EXPOSE 3000 3001

ENTRYPOINT ["/entrypoint-app.sh"]
CMD ["uv", "run", "python", "-m", "uvicorn", "app.main:socket_app", "--host", "0.0.0.0", "--port", "3000"]
