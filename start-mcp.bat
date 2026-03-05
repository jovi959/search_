@echo off
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

echo Starting MCP server...
echo   Endpoint: http://localhost:8000/mcp/
echo   Press Ctrl+C to stop
echo.

.venv\Scripts\python.exe mcp_server.py
pause
