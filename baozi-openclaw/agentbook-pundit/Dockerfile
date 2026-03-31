FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --production=false

COPY tsconfig.json ./
COPY src/ src/

RUN npx tsc

# --- Production stage ---
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --production && npm cache clean --force

COPY --from=builder /app/dist/ dist/

# Install @baozi.bet/mcp-server for MCP tool calls
RUN npm install -g @baozi.bet/mcp-server

ENV NODE_ENV=production

ENTRYPOINT ["node", "dist/cli.js"]
CMD ["run"]
