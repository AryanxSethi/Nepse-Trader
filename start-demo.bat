@echo off
cd /d D:\nepse-hermes-trader

echo NEPSE Hermes Trader - Starting services...
echo.

:: 1. Install/check Python dependencies
echo [1/6] Checking Python dependencies...
call venv\Scripts\activate.bat
pip install -r backend\requirements.txt --quiet 2>nul
echo Done.

:: 2. Start Ollama API if not running
tasklist /fi "imagename eq ollama.exe" 2>nul | find /i "ollama.exe" >nul
if errorlevel 1 (
    echo [2/6] Starting Ollama...
    start /b "" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    timeout /t 5 /nobreak >nul
) else (
    echo [2/6] Ollama already running
)

:: 3. Seed database if first run
if not exist data\nepse.db (
    echo [3/6] First run detected - seeding database with historical data...
    echo      This will take ~30 seconds...
    python -c "import asyncio; from data.seeder import seed; asyncio.run(seed())"
) else (
    echo [3/6] Database already seeded
)

:: 4. Clear pycache for fresh start
echo [4/6] Cleaning cached bytecode...
for /d /r backend %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d" 2>nul
echo Done.

:: 5. Start FastAPI backend
echo [5/6] Starting Backend (port 8001) and Frontend (port 5173)...
start "NEPSE Backend" /min cmd /c "cd /d D:\nepse-hermes-trader\backend && ..\venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

:: 6. Start Vite frontend
start "NEPSE Frontend" /min cmd /c "cd /d D:\nepse-hermes-trader\frontend && npm run dev"

:: 7. Open browser
timeout /t 6 /nobreak >nul
echo.
echo All services running!
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8001
echo   API Docs:  http://localhost:8001/docs
echo   Ollama:    http://localhost:11434
echo.
echo Press any key to stop all services...
echo.

start http://localhost:5173

pause

:: Stop services on keypress
echo Stopping services...
taskkill /f /im uvicorn.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
echo Done.
