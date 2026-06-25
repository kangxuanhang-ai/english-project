# syntax=docker/dockerfile:1

FROM node:20-alpine AS web-builder
WORKDIR /repo
RUN corepack enable pnpm

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages ./packages
COPY apps/tracker ./apps/tracker
COPY apps/web ./apps/web

ARG VITE_MINIO_ENDPOINT=http://localhost/minio
ARG VITE_SOCKET_URL=
ENV VITE_MINIO_ENDPOINT=$VITE_MINIO_ENDPOINT
ENV VITE_SOCKET_URL=$VITE_SOCKET_URL

RUN pnpm install --frozen-lockfile
RUN pnpm --filter @en/tracker build
RUN pnpm --filter @en/web build-only

FROM node:20-alpine AS admin-builder
WORKDIR /repo
RUN corepack enable pnpm

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages ./packages
COPY apps/admin ./apps/admin

ARG VITE_BASE=/admin/
ENV VITE_BASE=$VITE_BASE

RUN pnpm install --frozen-lockfile
RUN pnpm --filter @en/admin build

FROM nginx:1.27-alpine

COPY docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=web-builder /repo/apps/web/dist /usr/share/nginx/html/web
COPY --from=admin-builder /repo/apps/admin/dist /usr/share/nginx/html/admin

EXPOSE 80
