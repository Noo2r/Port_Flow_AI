#!/usr/bin/env bash
set -e

echo ""
echo " ====================================================="
echo "  PortFlow AI — One-Click Setup (Linux / macOS)"
echo " ====================================================="
echo ""

# ── Check Docker ──────────────────────────────────────────────────────────────
echo "[1/4] Checking Docker..."
if ! command -v docker &>/dev/null; then
    echo ""
    echo " ERROR: Docker is not installed."
    echo " Install it from: https://docs.docker.com/get-docker/"
    exit 1
fi
if ! docker info &>/dev/null; then
    echo ""
    echo " ERROR: Docker daemon is not running. Start it then re-run this script."
    exit 1
fi
echo " Docker OK"

# ── Pull base images ──────────────────────────────────────────────────────────
echo ""
echo "[2/4] Pulling base images..."
docker pull postgres:16-alpine
docker pull redis:7-alpine
docker pull nginx:alpine
docker pull python:3.12-slim
docker pull node:20-alpine

# ── Stop old containers ───────────────────────────────────────────────────────
echo ""
echo "[3/4] Stopping any previous PortFlow containers..."
docker compose down --remove-orphans 2>/dev/null || true

# ── Build and start ───────────────────────────────────────────────────────────
echo ""
echo "[4/4] Building and starting all services..."
echo " (Backend build: ~3-5 min first time)"
echo " (Frontend build: ~2-3 min first time)"
echo ""
docker compose up --build -d

# ── Wait for API ──────────────────────────────────────────────────────────────
echo ""
echo " Waiting for services to be ready..."
attempts=0
until curl -sf http://localhost:8000/health >/dev/null 2>&1; do
    attempts=$((attempts+1))
    if [ $attempts -ge 60 ]; then
        echo " Timeout — check logs: docker compose logs api"
        break
    fi
    sleep 3
done

echo ""
echo " ====================================================="
echo "  PortFlow AI is ready!"
echo " ====================================================="
echo ""
echo "  Frontend  ->  http://localhost:5173"
echo "  Backend   ->  http://localhost:8000"
echo "  API Docs  ->  http://localhost:8000/docs"
echo ""
echo "  Login:"
echo "    Email:    admin@portflow.ai"
echo "    Password: Admin1234!"
echo ""
echo "  To stop:       docker compose down"
echo "  To view logs:  docker compose logs -f"
echo ""

# Open browser (optional, works on mac; on linux may need xdg-open)
if command -v open &>/dev/null; then
    open http://localhost:5173
elif command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:5173
fi
