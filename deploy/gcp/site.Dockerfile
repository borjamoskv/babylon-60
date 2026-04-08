FROM node:20-bookworm-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci && npm install --no-save @rollup/rollup-linux-x64-gnu

COPY astro.config.mjs ./
COPY src/content.config.ts ./src/content.config.ts
COPY src ./src
COPY public ./public
COPY scripts/build-site.mjs ./scripts/build-site.mjs

ENV SITE_URL=https://cortexpersist.com

RUN npm run build

FROM nginx:1.27-alpine

COPY deploy/gcp/nginx-site.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
