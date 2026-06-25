@echo off
setlocal EnableDelayedExpansion
title PortFlow AI — Setup

echo.
echo  =====================================================
echo   PortFlow AI — One-Click Setup
echo  =====================================================
echo.

:: ── Check Docker ──────────────────────────────────────────────────────────────
echo [1/4] Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Docker is not installed or not in PATH.
    echo  Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    echo  Then re-run this script.
    echo.
    pause
    exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Docker Desktop is not running.
    echo  Please start Docker Desktop and wait for it to finish loading, then re-run this script.
    echo.
    pause
    exit /b 1
)
echo  Docker OK

:: ── Pull base images ──────────────────────────────────────────────────────────
echo.
echo [2/4] Pulling base images (postgres, redis, nginx, python, node)...
echo  This may take a few minutes on first run.
docker pull postgres:16-alpine
docker pull redis:7-alpine
docker pull nginx:alpine
docker pull python:3.12-slim
docker pull node:20-alpine

:: ── Stop any previous containers ─────────────────────────────────────────────
echo.
echo [3/4] Stopping any previous PortFlow containers...
docker compose down --remove-orphans 2>nul

:: ── Build and start ───────────────────────────────────────────────────────────
echo.
echo [4/4] Building and starting all services...
echo  (Backend build: ~3-5 min first time)
echo  (Frontend build: ~2-3 min first time)
echo.
docker compose up --build -d

if errorlevel 1 (
    echo.
    echo  ERROR: docker compose failed. Check logs with:
    echo    docker compose logs
    pause
    exit /b 1
)

:: ── Wait 15 seconds for services to start ────────────────────────────────────
echo.
echo  Waiting 15 seconds for services to start...
timeout /t 15 /nobreak >nul

:show_info
echo.
echo  =====================================================
echo   PortFlow AI is ready!
echo  =====================================================
echo.
echo   Frontend  ->  http://localhost:5173
echo   Backend   ->  http://localhost:8000
echo   API Docs  ->  http://localhost:8000/docs
echo.
echo   Login:
echo     Email:    admin@portflow.ai
echo     Password: Admin1234!
echo.
echo   To stop:   docker compose down
echo   To view logs: docker compose logs -f
echo.
start "" http://localhost:5173
pause
