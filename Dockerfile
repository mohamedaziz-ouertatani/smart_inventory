# Multi-stage build for Smart Inventory API (Fastify + TypeScript)
ARG NODE_VERSION=20

# --- Builder stage ---
FROM node:${NODE_VERSION}-alpine AS builder
WORKDIR /app

# Copy manifest and lockfile; use npm ci for deterministic installs
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

# --- Runtime stage ---
FROM node:${NODE_VERSION}-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy manifest and lockfile; install prod deps deterministically
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

# Copy compiled app
COPY --from=builder /app/dist ./dist

EXPOSE 3000
CMD ["node", "dist/server.js"]