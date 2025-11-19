@echo off
REM Script helper để chạy demo trên Windows

echo ================================================================================
echo CV-JD Matching System Demo Runner
echo ================================================================================
echo.

if "%1"=="" (
    echo Usage: run_demo.bat [simple^|full] cv_path jd_path
    echo.
    echo Examples:
    echo   run_demo.bat simple cv_candidate.pdf job_description.docx
    echo   run_demo.bat full ./sample_cvs job_description.docx
    echo.
    exit /b 1
)

if "%1"=="simple" (
    echo Running simple demo (1 CV + 1 JD)...
    echo.
    python demo_simple.py %2 %3
) else if "%1"=="full" (
    echo Running full demo (multiple CVs + 1 JD)...
    echo.
    python demo_matching.py %2 %3
) else (
    echo Invalid mode: %1
    echo Use 'simple' or 'full'
    exit /b 1
)

