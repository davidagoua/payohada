
FROM oven/bun:1 as builder

WORKDIR /app

COPY ./frontend/package.json ./frontend/bun.lock* ./
RUN bun install
COPY ./frontend/ .
ENV NUXT_PUBLIC_API_BASE=${NUXT_PUBLIC_API_BASE}
RUN bun run build


FROM caddy:latest as production

COPY --from=builder /app/dist /srv

COPY Caddyfile /etc/caddy/Caddyfile

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]