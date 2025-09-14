# ==========================
# Stage 0: Build frontend
# ==========================
FROM node:24 AS build-stage

WORKDIR /app

# Copier les fichiers de dépendances
COPY package*.json ./

# Installer les dépendances
RUN npm install

# Copier tout le code source
COPY ./ ./

# Passer la variable VITE_API_URL au build
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

# Build production (Vite)
RUN npm run build

# ==========================
# Stage 1: Nginx production
# ==========================
FROM nginx:1-alpine

# Copier le build React
COPY --from=build-stage /app/dist/ /usr/share/nginx/html

# Copier la configuration Nginx
COPY ./nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./nginx/nginx-default.conf /etc/nginx/conf.d/default.conf
# COPY ./nginx/nginx-backend-not-found.conf /etc/nginx/conf.d/backend-not-found.conf

# Exposer le port 3000
EXPOSE 3000

# Lancer Nginx en mode foreground
CMD ["nginx", "-g", "daemon off;"]
