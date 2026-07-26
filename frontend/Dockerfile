
FROM oven/bun:1

WORKDIR /app

COPY package.json bun.lock* ./
RUN bun install
COPY . .
ENV NUXT_PUBLIC_API_BASE=${NUXT_PUBLIC_API_BASE}
RUN bun run build
