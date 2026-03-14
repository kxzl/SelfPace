FROM node:20-slim AS builder

WORKDIR /app
COPY evidence/package.json ./
RUN npm install
COPY evidence/ .

# Copy parquet data needed by Evidence source queries at build time
COPY data/parquet /data/parquet
RUN npm run sources || true
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=builder /app/build /usr/share/nginx/html
COPY evidence/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1
