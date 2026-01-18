# Multi-stage build for Smart Inventory API (Fastify + TypeScript)
ARG NODE_VERSION=20

# --- Builder stage ---
FROM node:${NODE_VERSION}-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
# Use npm install instead of npm ci to avoid npm ci bug
RUN npm install
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

# --- Runtime stage ---
FROM node:${NODE_VERSION}-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
RUN npm install --omit=dev && npm cache clean --force
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ["node", "dist/server.js"]