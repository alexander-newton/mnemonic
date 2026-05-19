# Multi-stage Dockerfile for Mnemonic frontend
# Development stage uses npm run dev, production stage builds and serves

FROM node:20-alpine as dev
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 5173
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:5173/ || exit 1
CMD ["npm", "run", "dev"]

FROM node:20-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2-alpine as production
COPY --from=builder /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
EXPOSE 80 443
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1
