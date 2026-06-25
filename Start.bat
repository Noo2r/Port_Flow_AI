@echo off
title PortFlow AI - System Startup
color 0B

echo.
echo  ================================================
echo   PortFlow AI - Starting All Services
echo  ================================================
echo.

echo  [1/3] Starting Docker containers (DB, Redis, API)...
"C:\Program Files\Docker\Docker\resources\bin\docker.exe" --context desktop-linux compose -f "%~dp0Backend\docker-compose.yml" up -d

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Docker failed. Is Docker Desktop running?
    echo  Open Docker Desktop first, then run this script again.
    echo.
    pause
    exit /b 1
)

echo.
echo  [2/3] Waiting for API to be ready...
set /a attempts=0

:waitloop
set /a attempts+=1
timeout /t 2 /nobreak >nul
for /f %%i in ('curl -s -o nul -w "%%{http_code}" http://localhost:8000/ 2^>nul') do set status=%%i
if "%status%"=="200" goto apiready
if %attempts% geq 25 goto startfrontend
echo  Waiting... (%attempts%/25)
goto waitloop

:apiready
echo  API is online.

:startfrontend
echo.
echo  [3/3] Starting Frontend (http://localhost:5173)...
start "PortFlow Frontend" cmd /k "cd /d "%~dp0Frontend" && npm run dev"

timeout /t 3 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo  ================================================
echo   All services running!
echo.
echo   Frontend  -  http://localhost:5173
echo   API       -  http://localhost:8000
echo   API Docs  -  http://localhost:8000/docs
echo.
echo   Login: admin@portflow.ai / Admin1234!
echo  ================================================
echo.
pause