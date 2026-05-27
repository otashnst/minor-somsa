@echo off
echo ========================================
echo   MINOR SOMSA - Dispatch System
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Run the server
echo [*] Server ishga tushmoqda...
echo [*] Brauzerda oching: http://localhost:8000
echo.
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
