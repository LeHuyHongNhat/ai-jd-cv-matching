@echo off
REM Batch script để chạy Load Testing trên Windows
REM 
REM Usage: run_load_test.bat

echo ========================================
echo CV-JD MATCHING API - LOAD TEST
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python first: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python is installed
echo.

REM Menu
echo Choose Load Testing Method:
echo.
echo 1. Locust (Web UI) - Recommended
echo 2. Locust (Headless - No UI)
echo 3. Simple Load Test (Interactive)
echo 4. Install Load Testing Dependencies
echo 5. Start API Server (in new window)
echo 0. Exit
echo.

set /p choice="Enter your choice (0-5): "

if "%choice%"=="1" goto locust_web
if "%choice%"=="2" goto locust_headless
if "%choice%"=="3" goto simple_test
if "%choice%"=="4" goto install_deps
if "%choice%"=="5" goto start_server
if "%choice%"=="0" goto end
echo Invalid choice!
pause
exit /b 1

:locust_web
echo.
echo ========================================
echo Starting Locust with Web UI
echo ========================================
echo.
echo Locust will start on http://localhost:8089
echo.
echo Configuration:
echo   - Number of users: How many concurrent users to simulate
echo   - Spawn rate: How many users to add per second
echo   - Host: http://localhost:8000
echo.
echo Press Ctrl+C to stop
echo.
pause

REM Check if locust is installed
pip show locust >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Locust is not installed!
    echo Installing Locust...
    pip install locust
)

locust -f load_test_locust.py --host=http://localhost:8000
goto end

:locust_headless
echo.
echo ========================================
echo Locust Headless Mode
echo ========================================
echo.

set /p users="Number of users (default 100): "
if "%users%"=="" set users=100

set /p spawn_rate="Spawn rate (users/sec, default 10): "
if "%spawn_rate%"=="" set spawn_rate=10

set /p runtime="Run time (e.g. 60s, 5m, default 60s): "
if "%runtime%"=="" set runtime=60s

echo.
echo Running test with:
echo   Users: %users%
echo   Spawn rate: %spawn_rate% users/sec
echo   Run time: %runtime%
echo.
pause

REM Check if locust is installed
pip show locust >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Locust is not installed!
    echo Installing Locust...
    pip install locust
)

set timestamp=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =0%
set report_file=load_test_report_%timestamp%.html

locust -f load_test_locust.py --host=http://localhost:8000 --users %users% --spawn-rate %spawn_rate% --run-time %runtime% --headless --html=%report_file%

echo.
echo ========================================
echo Test completed!
echo Report saved to: %report_file%
echo ========================================
pause
goto end

:simple_test
echo.
echo ========================================
echo Simple Load Test (Interactive)
echo ========================================
echo.

REM Check if requests is installed
pip show requests >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: requests library is not installed!
    echo Installing requests...
    pip install requests
)

python load_test_simple.py
pause
goto end

:install_deps
echo.
echo ========================================
echo Installing Load Testing Dependencies
echo ========================================
echo.

if exist requirements_loadtest.txt (
    echo Installing from requirements_loadtest.txt...
    pip install -r requirements_loadtest.txt
    echo.
    echo ========================================
    echo Installation completed!
    echo ========================================
) else (
    echo requirements_loadtest.txt not found!
    echo Installing essential packages...
    pip install locust requests
)
echo.
pause
goto end

:start_server
echo.
echo ========================================
echo Starting API Server
echo ========================================
echo.

REM Check if uvicorn is installed
pip show uvicorn >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: uvicorn is not installed!
    echo Installing uvicorn...
    pip install uvicorn
)

echo Starting server in new window...
echo Server will run on http://localhost:8000
echo.
start cmd /k "uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo Server started in new window!
echo You can now run load tests.
echo.
pause
goto end

:end
echo.
echo Goodbye!
exit /b 0

