FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose port
EXPOSE 8000

# Entrypoint: auto-generate migration if none exist, then apply and start server
CMD ["sh", "-c", "if [ -z \"$(ls alembic/versions/*.py 2>/dev/null)\" ]; then alembic revision --autogenerate -m 'initial_schema'; fi && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
