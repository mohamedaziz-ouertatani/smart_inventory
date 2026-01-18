# Multi-stage build for Smart Inventory API (Fastify + TypeScript)
ARG NODE_VERSION=20

# --- Runtime stage ---
FROM node:${NODE_VERSION}-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY package.json package-lock.json ./
# Install production dependencies only
# npm ci/install has issues in this CI environment, using || true workaround
RUN npm ci --omit=dev || npm install --omit=dev
RUN npm cache clean --force
# Copy pre-built application
COPY dist ./dist
EXPOSE 3000
CMD ["node", "dist/server.js"]