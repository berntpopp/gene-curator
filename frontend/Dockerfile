# Base images are pinned by digest; Dependabot (docker ecosystem) bumps tag and digest together.
FROM node:24-alpine@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53 AS build-stage
WORKDIR /app

# Dependencies first: this layer is reused until the lockfile changes
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

COPY . .

ARG VITE_API_BASE_URL=http://localhost:8051
# Quick-login buttons expose seeded credentials: never on by default in a production image
ARG VITE_ENABLE_DEV_LOGIN=false
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_ENABLE_DEV_LOGIN=$VITE_ENABLE_DEV_LOGIN
RUN npm run build

# alpine-slim: no curl/njs, so fewer packages to patch
FROM nginx:alpine-slim@sha256:f45171d36c76a8b2f5ef97108a3a8a2294248a6578a0a180edc2d78f7d2edc26 AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
# Run as the image's unprivileged nginx user: it only needs its cache dir and pid file.
# Docker allows non-root binds below 1024 (net.ipv4.ip_unprivileged_port_start=0), so port 80 stays.
RUN chown -R nginx:nginx /var/cache/nginx \
    && touch /run/nginx.pid && chown nginx:nginx /run/nginx.pid
USER nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
