# syntax=docker/dockerfile:1
FROM node:24-alpine AS deps
WORKDIR /app
COPY package*.json ./
# npm ci reproducible; --omit=dev mantiene la imagen pequeña
RUN npm install --omit=dev && npm cache clean --force

FROM node:24-alpine
ENV NODE_ENV=production
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY src ./src
# Ejecutar como usuario sin privilegios (buena práctica de seguridad)
USER node
EXPOSE 4000
CMD ["node", "src/server.js"]
