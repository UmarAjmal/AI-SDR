<#
.SYNOPSIS
    Codenter AI SDR Platform - PowerShell Server Controller
.DESCRIPTION
    Interactive CLI menu to start, stop, kill previous, restart, and monitor
    the FastAPI Backend (port 8000) and Vite React Frontend (port 5173).
#>
param([string]$Command)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

$RunDir = Join-Path $ScriptDir ".run"
if (-not (Test-Path $RunDir)) {
    New-Item -ItemType Directory -Path $RunDir -Force | Out-Null
}

$BackendLog = Join-Path $RunDir "backend.log"
$FrontendLog = Join-Path $RunDir "frontend.log"

# Locate Python in .venv
$PythonBin = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonBin)) {
    $PythonBin = "python"
}

function Kill-Port([int]$Port) {
    Write-Host "Checking for active processes on port $Port..." -ForegroundColor Yellow
    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in $pids) {
            if ($procId -gt 0) {
                Write-Host "  Killing PID $procId on port $Port..." -ForegroundColor Red
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Test-PortInUse([int]$Port) {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return ($null -ne $conn)
}

function Start-BackendServer {
    Write-Host "`n--------------------------------------------------" -ForegroundColor Cyan
    Write-Host "Starting FastAPI Backend (Port 8000)..." -ForegroundColor White
    Write-Host "--------------------------------------------------" -ForegroundColor Cyan

    if (Test-PortInUse 8000) {
        Write-Host "Port 8000 is in use! Stopping previous instance..." -ForegroundColor Yellow
        Kill-Port 8000
        Start-Sleep -Seconds 1
    }

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "cmd.exe"
    $startInfo.Arguments = "/c `"$PythonBin -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload > `"$BackendLog`" 2>&1`""
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $startInfo.CreateNoWindow = $true
    [System.Diagnostics.Process]::Start($startInfo) | Out-Null

    Write-Host "Waiting for backend to initialize..."
    Start-Sleep -Seconds 2

    if (Test-PortInUse 8000) {
        Write-Host "✓ Backend successfully started!" -ForegroundColor Green
        Write-Host "  URL:  http://127.0.0.1:8000" -ForegroundColor White
        Write-Host "  Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
        Write-Host "  Logs: $BackendLog" -ForegroundColor Gray
    } else {
        Write-Host "Backend is initializing. Check logs if needed: $BackendLog" -ForegroundColor Yellow
    }
}

function Start-FrontendServer {
    Write-Host "`n--------------------------------------------------" -ForegroundColor Cyan
    Write-Host "Starting Vite React Frontend (Port 5173)..." -ForegroundColor White
    Write-Host "--------------------------------------------------" -ForegroundColor Cyan

    if (Test-PortInUse 5173) {
        Write-Host "Port 5173 is in use! Stopping previous instance..." -ForegroundColor Yellow
        Kill-Port 5173
        Start-Sleep -Seconds 1
    }

    $webDir = Join-Path $ScriptDir "apps\web"
    $viteCache = Join-Path $webDir "node_modules\.vite"
    if (Test-Path $viteCache) {
        Remove-Item -Recurse -Force $viteCache -ErrorAction SilentlyContinue
    }

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = "cmd.exe"
    $startInfo.Arguments = "/c `"cd /d `"$webDir`" && npm run dev > `"$FrontendLog`" 2>&1`""
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
    $startInfo.CreateNoWindow = $true
    [System.Diagnostics.Process]::Start($startInfo) | Out-Null

    Write-Host "Waiting for Vite to compile..."
    Start-Sleep -Seconds 3

    Write-Host "✓ Frontend launch initiated!" -ForegroundColor Green
    Write-Host "  URL:  http://localhost:5173" -ForegroundColor White
    Write-Host "  Logs: $FrontendLog" -ForegroundColor Gray
}

function Stop-AllServers {
    Write-Host "`n--------------------------------------------------" -ForegroundColor Red
    Write-Host "Stopping All Servers & Freeing Ports..." -ForegroundColor White
    Write-Host "--------------------------------------------------" -ForegroundColor Red

    Kill-Port 8000
    Kill-Port 5173

    Write-Host "✓ All previous servers stopped! Ports 8000 and 5173 are free.`n" -ForegroundColor Green
}

function Show-Status {
    Write-Host "`n==================================================" -ForegroundColor Blue
    Write-Host "SERVER STATUS CHECK" -ForegroundColor White
    Write-Host "==================================================" -ForegroundColor Blue

    if (Test-PortInUse 8000) {
        Write-Host "  Backend (FastAPI) : " -NoNewline
        Write-Host "● RUNNING" -ForegroundColor Green -NoNewline
        Write-Host " on http://127.0.0.1:8000"
    } else {
        Write-Host "  Backend (FastAPI) : " -NoNewline
        Write-Host "○ STOPPED" -ForegroundColor Red -NoNewline
        Write-Host " (Port 8000 free)"
    }

    if (Test-PortInUse 5173) {
        Write-Host "  Frontend (Vite)   : " -NoNewline
        Write-Host "● RUNNING" -ForegroundColor Green -NoNewline
        Write-Host " on http://localhost:5173"
    } else {
        Write-Host "  Frontend (Vite)   : " -NoNewline
        Write-Host "○ STOPPED" -ForegroundColor Red -NoNewline
        Write-Host " (Port 5173 free)"
    }
    Write-Host "==================================================`n" -ForegroundColor Blue
}

function Show-Logs([string]$LogPath, [string]$ServerName) {
    Write-Host "`n--- Last 25 lines of $ServerName Logs ---" -ForegroundColor Cyan
    if (Test-Path $LogPath) {
        Get-Content $LogPath -Tail 25
    } else {
        Write-Host "No log file found at $LogPath" -ForegroundColor Gray
    }
    Write-Host "-------------------------------------------`n" -ForegroundColor Cyan
}

function Show-Menu {
    Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║         CODENTER AI SDR - SERVER CONTROL         ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host "  1) Start Both Servers (Backend + Frontend)" -ForegroundColor Green
    Write-Host "  2) Start Backend Only (FastAPI :8000)"
    Write-Host "  3) Start Frontend Only (Vite React :5173)"
    Write-Host "  4) Stop All Servers (Kill Ports 8000 & 5173)" -ForegroundColor Yellow
    Write-Host "  5) Restart Both Servers" -ForegroundColor Magenta
    Write-Host "  6) Check Server Status" -ForegroundColor Cyan
    Write-Host "  7) View Backend Logs" -ForegroundColor Gray
    Write-Host "  8) View Frontend Logs" -ForegroundColor Gray
    Write-Host "  0) Exit" -ForegroundColor Red
    Write-Host "──────────────────────────────────────────────────" -ForegroundColor Cyan
}

# Parameter dispatch if passed via CLI
if ($Command -eq "start") {
    Start-BackendServer
    Start-FrontendServer
    exit 0
} elseif ($Command -eq "stop") {
    Stop-AllServers
    exit 0
} elseif ($Command -eq "restart") {
    Stop-AllServers
    Start-Sleep -Seconds 1
    Start-BackendServer
    Start-FrontendServer
    exit 0
} elseif ($Command -eq "status") {
    Show-Status
    exit 0
}

# Interactive Menu Loop
while ($true) {
    Show-Menu
    $choice = Read-Host "Select an option [0-8]"
    switch ($choice) {
        "1" { Start-BackendServer; Start-FrontendServer; Write-Host "" }
        "2" { Start-BackendServer; Write-Host "" }
        "3" { Start-FrontendServer; Write-Host "" }
        "4" { Stop-AllServers }
        "5" { Stop-AllServers; Start-Sleep -Seconds 1; Start-BackendServer; Start-FrontendServer; Write-Host "" }
        "6" { Show-Status }
        "7" { Show-Logs $BackendLog "Backend" }
        "8" { Show-Logs $FrontendLog "Frontend" }
        "0" { Write-Host "Exiting. Have a great day!" -ForegroundColor Green; exit 0 }
        default { Write-Host "Invalid option! Please enter a number between 0 and 8.`n" -ForegroundColor Red }
    }
}
