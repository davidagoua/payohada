
FROM oven/bun:1 as builder

WORKDIR /app

COPY package.json bun.lock* ./
RUN bun install
COPY . .
ENV NUXT_PUBLIC_API_BASE=${NUXT_PUBLIC_API_BASE}
RUN bun run build


FROM caddy:latest as production

COPY --from=builder /app/dist /srv

COPY ../Caddyfile /etc/caddy/Caddyfile

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]