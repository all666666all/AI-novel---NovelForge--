# ============================================
# Stage 1 — build the frontend static assets
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# Install dependencies from the lockfile for reproducible builds
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund

# Build the frontend
COPY frontend/ ./
RUN npm run build

# ============================================
# Stage 2 — final image (backend + nginx)
# ============================================
FROM python:3.11-slim

WORKDIR /app

# System dependencies: nginx, supervisor, curl, MySQL client headers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (base + optional MySQL driver, since the image supports both backends)
COPY backend/requirements.txt backend/requirements-mysql.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-mysql.txt

# 复制后端应用代码
COPY backend/ ./

# Start with a clean storage dir so the admin password is seeded from env on first boot
RUN rm -rf /app/storage && mkdir -p /app/storage

# Copy the built frontend into nginx's web root
COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html

# Deployment configuration
COPY deploy/nginx.conf /etc/nginx/sites-available/default
COPY deploy/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY deploy/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Run as a non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

EXPOSE 80

# supervisor launches both nginx and uvicorn
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
