@echo off
echo ========================================
echo   MINOR SOMSA - O'rnatish
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [XATO] Python topilmadi! https://python.org dan o'rnating.
    pause
    exit
)

echo [1/3] Virtual muhit yaratilmoqda...
python -m venv venv
call venv\Scripts\activate

echo [2/3] Kutubxonalar o'rnatilmoqda...
pip install -r requirements.txt

echo [3/3] Tayyor!
echo.
echo Ishga tushirish uchun: start.bat
echo.
pause
