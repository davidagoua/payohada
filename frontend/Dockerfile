# Étape 1 : Construction de l'application Nuxt
FROM node:20-slim AS builder

WORKDIR /app

# Installer pnpm globalement
RUN npm install -g pnpm

# Copier les fichiers de dépendances
COPY package.json pnpm-lock.yaml* ./

# Installer toutes les dépendances
RUN pnpm install --frozen-lockfile

# Copier le reste des fichiers du projet
COPY . .

# Définir NUXT_PUBLIC_API_BASE pour le build statique
ENV NUXT_PUBLIC_API_BASE=/api

# Générer les fichiers statiques de l'application Nuxt (SSG)
RUN npx nuxt generate

# Étape 2 : Image minimale pour exposer les fichiers statiques via un volume partagé
FROM alpine:latest

WORKDIR /var/www/html

# Copier les fichiers statiques générés depuis l'étape builder
COPY --from=builder /app/.output/public /static

# Copier les fichiers dans le volume partagé au démarrage
CMD sh -c "cp -rp /static/. /var/www/html/ && echo 'Fichiers statiques copiés.' && tail -f /dev/null"
