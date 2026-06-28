
FROM oven/bun:1 AS base

WORKDIR /app

COPY package.json bun.lock* ./
RUN bun install
COPY . .
ENV NUXT_PUBLIC_API_BASE=/api
RUN bun run generate
