# syntax=docker/dockerfile:1
FROM node:20-slim AS builder

WORKDIR /app

ARG APP_SECRET_PATH=""
ENV NEXT_PUBLIC_APP_SECRET_PATH=${APP_SECRET_PATH}

# 1. Install dependencies (glibc compatible, resolving linux bindings)
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    npm install --legacy-peer-deps

# 2. Copy source code files explicitly
COPY tsconfig.json components.json next.config.ts postcss.config.mjs eslint.config.mjs ./
COPY public ./public
COPY src ./src

# 3. Build Next.js production bundle
RUN npm run build

# 4. Production runtime image
FROM node:20-slim AS runner
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000

COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npx", "next", "start", "--port", "3000"]
