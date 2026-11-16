@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0add_revit_mcp.ps1" > "%~dp0add_revit_mcp.log" 2>&1
echo EXITCODE=%errorlevel% >> "%~dp0add_revit_mcp.log"
