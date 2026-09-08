# syntax=docker/dockerfile:1

FROM node:20-slim AS builder

WORKDIR /app

ARG APP_SECRET_PATH=""
ENV NEXT_PUBLIC_APP_SECRET_PATH=${APP_SECRET_PATH}

# Use Liara's Iranian npm mirror
RUN npm config set registry https://package-mirror.liara.ir/repository/npm/

# Install dependencies
COPY package.json package-lock.json* ./

RUN --mount=type=cache,target=/root/.npm \
    npm install --legacy-peer-deps

# Copy source
COPY tsconfig.json components.json next.config.ts postcss.config.mjs eslint.config.mjs ./
COPY public ./public
COPY src ./src

# Build Next.js
RUN npm run build


# ============================================================
# Production runtime
# ============================================================

FROM node:20-slim AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000

# Use Liara's Iranian npm mirror
RUN npm config set registry https://package-mirror.liara.ir/repository/npm/

COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npx", "next", "start", "--port", "3000"]