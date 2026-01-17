# Multi-stage build for Smart Inventory API (Fastify + TypeScript)
ARG NODE_VERSION=20

# --- Builder stage: install deps and compile TypeScript ---
FROM node:${NODE_VERSION}-alpine AS builder
WORKDIR /app

# Install dependencies (dev deps included for build)
COPY package.json tsconfig.json ./
# If you later add a package-lock.json, switch to: RUN npm ci
RUN npm install

# Copy source and build
COPY src ./src
RUN npm run build

# --- Runtime stage: production image with compiled JS ---
FROM node:${NODE_VERSION}-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy package manifest and install only production deps
COPY package.json ./
# If you later add a package-lock.json, switch to: RUN npm ci --omit=dev
RUN npm install --omit=dev && npm cache clean --force

# Copy compiled app from builder
COPY --from=builder /app/dist ./dist

# Expose API port
EXPOSE 3000

# Default command
CMD ["node", "dist/server.js"]