
FROM oven/bun:1 as builder

WORKDIR /app

COPY ./frontend/package.json ./frontend/bun.lock* ./
RUN bun install
COPY ./frontend/ .
ARG NUXT_PUBLIC_API_BASE
ARG NUXT_PUBLIC_SUPABASE_URL
ARG NUXT_PUBLIC_SUPABASE_ANON_KEY
ARG NUXT_PUBLIC_BUGSINK_DSN
ENV NUXT_PUBLIC_API_BASE=${NUXT_PUBLIC_API_BASE}
ENV NUXT_PUBLIC_SUPABASE_URL=${NUXT_PUBLIC_SUPABASE_URL}
ENV NUXT_PUBLIC_SUPABASE_ANON_KEY=${NUXT_PUBLIC_SUPABASE_ANON_KEY}
ENV NUXT_PUBLIC_BUGSINK_DSN=${NUXT_PUBLIC_BUGSINK_DSN}
RUN bun run build
RUN ls /app/


FROM caddy:latest as production

COPY --from=builder /app/.output/public /srv

COPY Caddyfile /etc/caddy/Caddyfile

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]