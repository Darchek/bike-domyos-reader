# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Clone the GitHub repo
# Replace ARG values via --build-arg or override in docker-compose
ARG GITHUB_REPO_URL=https://github.com/your-org/your-repo.git
ARG GITHUB_BRANCH=main

RUN git clone --depth 1 --branch ${GITHUB_BRANCH} ${GITHUB_REPO_URL} .

# Install Python dependencies into a separate layer
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local
# Copy application source
COPY --from=builder /app /app

# Create a non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# The .env file is injected at runtime via docker-compose (env_file directive).
# Never COPY .env into the image.

EXPOSE 8000

# Uvicorn with production-friendly settings.
# Override APP_MODULE if your entrypoint differs (e.g. src.main:app).
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]