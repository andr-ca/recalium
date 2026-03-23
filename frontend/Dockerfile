# syntax=docker/dockerfile:1
# Frontend build container — produces ./dist for copy into backend image.
FROM node:22-alpine AS builder

RUN npm install -g pnpm@10.32.1

WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm build

FROM scratch AS export
COPY --from=builder /app/frontend/dist /dist
