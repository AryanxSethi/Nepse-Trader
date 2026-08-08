@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo NEPSE Trader - Starting services...
echo.

:: 1. Install/check Python dependencies (venv)
echo [1/6] Checking Python venv...
if not exist "backend\venv\Scripts\python.exe" (
    echo Creating Python venv...
    python -m venv backend\venv
)
echo Installing/updating dependencies...
call backend\venv\Scripts\pip install -r backend\requirements.txt --quiet 2>nul
echo Done.

:: 2. Start Ollama API if not running
tasklist /fi "imagename eq ollama.exe" 2>nul | find /i "ollama.exe" >nul
if errorlevel 1 (
    echo [2/6] Starting Ollama...
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        start /b "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    ) else (
        echo Ollama not found — LLM chat will be unavailable.
    )
) else (
    echo [2/6] Ollama already running
)

:: 3. Seed database if first run
if not exist backend\data\nepse.db (
    echo [3/6] First run detected - seeding database...
    set PYTHONPATH=%CD%\backend
    backend\venv\Scripts\python -c "import asyncio; from app.db.seeder import seed; asyncio.run(seed())"
) else (
    echo [3/6] Database already seeded
)

:: 4. Clear pycache for fresh start
echo [4/6] Cleaning cached bytecode...
for /d /r backend %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
echo Done.

:: 5. Start FastAPI backend (venv)
echo [5/6] Starting Backend (port 8001)...
for /f "tokens=5" %%a in ('netstat -ano ^| find ":8001" ^| find "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
powershell -Command "Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }" 2>nul
set PYTHONPATH=%CD%\backend
start "NEPSE Backend" cmd /c "cd /d %~dp0backend && venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8001"

:: 6. Start Vite frontend
echo [6/6] Starting Frontend (port 5173)...
start "NEPSE Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

:: 7. Wait for backend health check
echo Waiting for backend to be ready...
set RETRIES=0
:wait_loop
if !RETRIES! geq 30 (
    echo [ERROR] Backend failed to start after 60 seconds.
    echo Check that port 8001 is not in use and venv is functional.
    pause
    exit /b 1
)
timeout /t 2 /nobreak >nul
backend\venv\Scripts\python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/api/health')" >nul 2>&1
if errorlevel 1 (
    set /a RETRIES+=1
    goto wait_loop
)

:: 8. Open browser
echo.
echo All services running!
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8001
echo   API Docs:  http://localhost:8001/docs
start http://localhost:5173

echo.
echo Press Ctrl+C in this window to stop all services...
echo.

:: 9. Wait for user, then kill by window title
pause >nul
echo Stopping services...
taskkill /f /fi "WINDOWTITLE eq NEPSE Backend*" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq NEPSE Frontend*" >nul 2>&1
echo Done.
