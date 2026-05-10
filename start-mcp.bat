@echo off
setlocal EnableDelayedExpansion

echo.
echo ========================================
echo  Web Search Agent - MCP Server
echo ========================================
echo.

if not exist .venv\Scripts\python.exe (
    echo [X] .venv not found. Run setup.bat first.
    pause
    exit /b 1
)

set "MCP_PORT=8000"
for /f "tokens=2 delims==" %%p in ('findstr /b /i "MCP_PORT=" .env 2^>nul') do set "MCP_PORT=%%~p"
set "MCP_PORT=!MCP_PORT: =!"

echo Freeing port !MCP_PORT! if anything is listening...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$port='%MCP_PORT%'; if ($port -notmatch '^\d+$') { $port='8000' }; $listeners=@(Get-NetTCPConnection -LocalPort ([int]$port) -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); foreach ($procId in $listeners) { try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Host ('  killed PID ' + $procId) } catch { } }"

echo.

echo Starting MCP server...
echo   Endpoint: http://localhost:!MCP_PORT!/mcp/
echo   Press Ctrl+C to stop
echo.

.venv\Scripts\python.exe mcp_server.py
pause
