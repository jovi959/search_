@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo  Web Search Agent - Project Setup
echo ========================================
echo.

:: ------------------------------------------
:: Check prerequisites
:: ------------------------------------------

echo [Prerequisites] Checking required tools...
echo.

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo   [X] Node.js    NOT FOUND
    echo       Install from https://nodejs.org/
    set "MISSING=1"
) else (
    for /f "tokens=*" %%v in ('node --version') do echo   [OK] Node.js   %%v
)

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo   [X] npm        NOT FOUND
    echo       Comes with Node.js - reinstall Node
    set "MISSING=1"
) else (
    for /f "tokens=*" %%v in ('npm --version') do echo   [OK] npm       %%v
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [X] Python     NOT FOUND
    echo       Install from https://www.python.org/downloads/
    set "MISSING=1"
) else (
    for /f "tokens=*" %%v in ('python --version') do echo   [OK] %%v
)

where pip >nul 2>&1
if %errorlevel% neq 0 (
    echo   [X] pip        NOT FOUND
    echo       Reinstall Python with "Add to PATH" checked
    set "MISSING=1"
) else (
    for /f "tokens=*" %%v in ('pip --version') do echo   [OK] pip       %%v
)

echo.

if defined MISSING (
    echo ========================================
    echo  SETUP ABORTED - install missing tools
    echo ========================================
    pause
    exit /b 1
)

echo All prerequisites found.
echo.

:: ------------------------------------------
:: Detect what is already installed
:: ------------------------------------------

set "NODE_DONE=0"
set "VENV_DONE=0"
set "PIP_DONE=0"

if exist node_modules\promptfoo (
    set "NODE_DONE=1"
)

if exist .venv\Scripts\python.exe (
    set "VENV_DONE=1"
)

if "!VENV_DONE!"=="1" (
    .venv\Scripts\python -c "import openai" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PIP_DONE=1"
    )
)

if "!NODE_DONE!"=="1" if "!VENV_DONE!"=="1" if "!PIP_DONE!"=="1" (
    echo ----------------------------------------
    echo  Everything is already installed:
    echo.
    echo   [OK] node_modules  (promptfoo found)
    echo   [OK] .venv         (exists)
    echo   [OK] openai        (importable)
    echo ----------------------------------------
    echo.
    choice /C YN /M "Reinstall anyway? (Y/N)"
    if !errorlevel! equ 2 (
        echo.
        echo Skipping install. You're good to go!
        echo.
        echo   npm run eval        Run all tests
        echo   npm run view        Open results in browser
        echo.
        pause
        exit /b 0
    )
    echo.
) else (
    echo ----------------------------------------
    echo  Current state:
    echo.
    if "!NODE_DONE!"=="1" (
        echo   [OK] node_modules  already installed
    ) else (
        echo   [--] node_modules  not installed
    )
    if "!VENV_DONE!"=="1" (
        echo   [OK] .venv         already exists
    ) else (
        echo   [--] .venv         not created
    )
    if "!PIP_DONE!"=="1" (
        echo   [OK] openai        already installed
    ) else (
        echo   [--] openai        not installed
    )
    echo ----------------------------------------
    echo.
)

:: ------------------------------------------
:: Step 1: Node dependencies
:: ------------------------------------------

echo ----------------------------------------
echo [1/3] Installing Node dependencies...
echo ----------------------------------------

if not exist package.json (
    echo   [X] FAILED - package.json not found
    echo       Are you running this from the project root?
    pause
    exit /b 1
)

if "!NODE_DONE!"=="1" (
    choice /C YN /M "  node_modules exists. Reinstall? (Y/N)"
    if !errorlevel! equ 2 (
        echo   [OK] Skipped - keeping existing node_modules
        goto :step2
    )
)

call npm install 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   [X] FAILED - npm install
    echo       Check the error above. Common fixes:
    echo         - Delete node_modules and try again
    echo         - Run "npm cache clean --force"
    pause
    exit /b 1
)
echo   [OK] Node dependencies installed
echo.

:: ------------------------------------------
:: Step 2: Python virtual environment
:: ------------------------------------------

:step2
echo.
echo ----------------------------------------
echo [2/3] Setting up Python virtual environment...
echo ----------------------------------------

if "!VENV_DONE!"=="1" (
    choice /C YN /M "  .venv exists. Recreate? (Y/N)"
    if !errorlevel! equ 2 (
        echo   [OK] Skipped - keeping existing .venv
        goto :step3
    )
    echo   Removing old .venv...
    rmdir /s /q .venv
)

python -m venv .venv 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   [X] FAILED - could not create .venv
    echo       Common fixes:
    echo         - Make sure Python 3.10+ is installed
    echo         - Run "python -m ensurepip"
    pause
    exit /b 1
)
echo   [OK] Created .venv
echo.

:: ------------------------------------------
:: Step 3: Python dependencies
:: ------------------------------------------

:step3
echo.
echo ----------------------------------------
echo [3/3] Installing Python dependencies...
echo ----------------------------------------

if not exist requirements.txt (
    echo   [X] FAILED - requirements.txt not found
    pause
    exit /b 1
)

call .venv\Scripts\activate
if %errorlevel% neq 0 (
    echo.
    echo   [X] FAILED - could not activate .venv
    echo       Try deleting .venv and running setup again
    pause
    exit /b 1
)

pip install -r requirements.txt 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   [X] FAILED - pip install
    echo       Check the error above. Common fixes:
    echo         - Upgrade pip: python -m pip install --upgrade pip
    echo         - Check your internet connection
    pause
    exit /b 1
)
echo   [OK] Python dependencies installed
echo.

:: ------------------------------------------
:: Verify everything works
:: ------------------------------------------

echo ----------------------------------------
echo Verifying setup...
echo ----------------------------------------

call npx promptfoo --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   [X] Promptfoo not working
) else (
    for /f "tokens=*" %%v in ('npx promptfoo --version 2^>nul') do echo   [OK] Promptfoo %%v
)

.venv\Scripts\python -c "import openai; print('  [OK] openai', openai.__version__)" 2>&1
if %errorlevel% neq 0 (
    echo   [X] openai package not working
)

echo.
echo ========================================
echo  Setup complete!
echo.
echo  Quick start:
echo    npm run eval        Run all tests
echo    npm run view        Open results in browser
echo.
echo  Debug a single test:
echo    npx promptfoo eval --no-cache -c promptfooconfig-debug.yaml
echo ========================================
pause
