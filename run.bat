@echo off
REM Flask Application Startup Script for Windows

echo.
echo ========================================
echo  Radio Schedule Flask Application
echo ========================================
echo.

REM Navigate to project directory
cd /d "%~dp0"

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Start Flask app
echo.
echo ========================================
echo  Starting Flask Application...
echo ========================================
echo.
echo The application will be available at:
echo   http://localhost:5005
echo.
echo Press Ctrl+C to stop the application
echo ========================================
echo.

python app.py

pause
