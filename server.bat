@echo off
setlocal enabledelayedexpansion

:: ============================================================================
:: Codenter AI SDR Platform - Windows Batch Server Controller
:: Controls FastAPI Backend (:8000) and Vite React Frontend (:5173)
:: ============================================================================

cd /d "%~dp0"
if not exist ".run" mkdir .run

:MENU
cls
echo =======================================================
echo          CODENTER AI SDR - WINDOWS SERVER CONTROL
echo =======================================================
echo  [1] Start Both Servers (Backend + Frontend)
echo  [2] Start Backend Only (FastAPI on Port 8000)
echo  [3] Start Frontend Only (Vite React on Port 5173)
echo  [4] Stop All Servers (Kill Ports 8000 ^& 5173)
echo  [5] Restart Both Servers
echo  [6] Check Server Status
echo  [7] View Backend Logs
echo  [8] View Frontend Logs
echo  [0] Exit
echo =======================================================
set /p choice="Enter option [0-8]: "

if "%choice%"=="1" goto START_ALL
if "%choice%"=="2" goto START_BACKEND
if "%choice%"=="3" goto START_FRONTEND
if "%choice%"=="4" goto STOP_ALL
if "%choice%"=="5" goto RESTART_ALL
if "%choice%"=="6" goto STATUS
if "%choice%"=="7" goto LOGS_BACKEND
if "%choice%"=="8" goto LOGS_FRONTEND
if "%choice%"=="0" goto EXIT
goto MENU

:START_BACKEND
echo.
echo -------------------------------------------------------
echo Starting FastAPI Backend (Port 8000)...
echo -------------------------------------------------------
call :KILL_PORT 8000
set PYTHON_CMD=.venv\Scripts\python.exe
if not exist "%PYTHON_CMD%" set PYTHON_CMD=python

start "Codenter AI SDR - Backend" /min cmd /c "%PYTHON_CMD% -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload > .run\backend.log 2>&1"
timeout /t 2 /nobreak >nul
echo Backend is running:
echo   URL:  http://127.0.0.1:8000
echo   Docs: http://127.0.0.1:8000/docs
echo   Logs: .run\backend.log
echo.
pause
goto MENU

:START_FRONTEND
echo.
echo -------------------------------------------------------
echo Starting Vite Frontend (Port 5173)...
echo -------------------------------------------------------
call :KILL_PORT 5173
start "Codenter AI SDR - Frontend" /min cmd /c "cd apps\web && npm run dev > ..\..\.run\frontend.log 2>&1"
timeout /t 3 /nobreak >nul
echo Frontend is running:
echo   URL:  http://localhost:5173
echo   Logs: .run\frontend.log
echo.
pause
goto MENU

:START_ALL
echo.
echo -------------------------------------------------------
echo Starting Both Backend and Frontend Servers...
echo -------------------------------------------------------
call :KILL_PORT 8000
call :KILL_PORT 5173

set PYTHON_CMD=.venv\Scripts\python.exe
if not exist "%PYTHON_CMD%" set PYTHON_CMD=python

start "Codenter AI SDR - Backend" /min cmd /c "%PYTHON_CMD% -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload > .run\backend.log 2>&1"
start "Codenter AI SDR - Frontend" /min cmd /c "cd apps\web && npm run dev > ..\..\.run\frontend.log 2>&1"

timeout /t 3 /nobreak >nul
echo Servers are up!
echo   Frontend: http://localhost:5173
echo   Backend:  http://127.0.0.1:8000
echo   API Docs: http://127.0.0.1:8000/docs
echo.
pause
goto MENU

:STOP_ALL
echo.
echo -------------------------------------------------------
echo Stopping All Running Servers and Freeing Ports...
echo -------------------------------------------------------
call :KILL_PORT 8000
call :KILL_PORT 5173
echo.
echo All previous servers have been terminated. Ports 8000 and 5173 are free.
echo.
pause
goto MENU

:RESTART_ALL
echo.
echo Restarting servers...
call :KILL_PORT 8000
call :KILL_PORT 5173
timeout /t 1 /nobreak >nul
goto START_ALL

:STATUS
cls
echo =======================================================
echo                  SERVER STATUS
echo =======================================================
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo   Backend (FastAPI) : [ RUNNING ] on http://127.0.0.1:8000
) else (
    echo   Backend (FastAPI) : [ STOPPED ] (Port 8000 free)
)

netstat -ano | findstr ":5173" | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo   Frontend (Vite)   : [ RUNNING ] on http://localhost:5173
) else (
    echo   Frontend (Vite)   : [ STOPPED ] (Port 5173 free)
)
echo =======================================================
echo.
pause
goto MENU

:LOGS_BACKEND
cls
echo --- Last 25 lines of Backend Logs (.run\backend.log) ---
if exist ".run\backend.log" (
    powershell -Command "Get-Content .run\backend.log -Tail 25"
) else (
    echo No backend logs found.
)
echo ----------------------------------------------------------
echo.
pause
goto MENU

:LOGS_FRONTEND
cls
echo --- Last 25 lines of Frontend Logs (.run\frontend.log) ---
if exist ".run\frontend.log" (
    powershell -Command "Get-Content .run\frontend.log -Tail 25"
) else (
    echo No frontend logs found.
)
echo ----------------------------------------------------------
echo.
pause
goto MENU

:KILL_PORT
set TARGET_PORT=%1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%TARGET_PORT% " ^| findstr "LISTENING"') do (
    echo Killing process %%a using port %TARGET_PORT%...
    taskkill /f /pid %%a >nul 2>&1
)
goto :eof

:EXIT
echo Exiting. Goodbye!
exit /b 0
