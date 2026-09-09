#!/usr/bin/env bash

# ==============================================================================
# Codenter AI SDR Platform - Interactive Server Controller
# Controls FastAPI Backend (port 8000) and Vite React Frontend (port 5173)
# ==============================================================================

# Determine Script Directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Setup Runtime Directory for Logs and PIDs
RUN_DIR="$SCRIPT_DIR/.run"
mkdir -p "$RUN_DIR"

BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"

# Color Codes
GREEN="\033[1;32m"
RED="\033[1;31m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
CYAN="\033[1;36m"
BOLD="\033[1m"
RESET="\033[0m"

# Locate Python in Virtualenv
if [ -f "$SCRIPT_DIR/.venv/Scripts/python.exe" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/Scripts/python.exe"
elif [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python"
fi

# Function: Kill process listening on a specific port
kill_port() {
    local port=$1
    echo -e "${YELLOW}Cleaning up any process running on port $port...${RESET}"

    # Windows / Git Bash / MSYS detection
    if command -v netstat.exe &>/dev/null || command -v netstat &>/dev/null; then
        # Find PIDs using netstat
        local pids
        pids=$(netstat -ano 2>/dev/null | grep -E "LISTENING.*:$port|:$port.*LISTENING" | awk '{print $NF}' | sort -u)
        if [ -n "$pids" ]; then
            for pid in $pids; do
                if [ "$pid" != "0" ] && [ -n "$pid" ]; then
                    echo -e "  Killing Windows PID $pid on port $port..."
                    taskkill //F //PID "$pid" &>/dev/null || taskkill /F /PID "$pid" &>/dev/null || true
                fi
            done
        fi
    fi

    # Unix / Linux / macOS detection
    if command -v lsof &>/dev/null; then
        local unix_pids
        unix_pids=$(lsof -ti :"$port" 2>/dev/null)
        if [ -n "$unix_pids" ]; then
            for pid in $unix_pids; do
                echo -e "  Killing Unix PID $pid on port $port..."
                kill -9 "$pid" &>/dev/null || true
            done
        fi
    elif command -v fuser &>/dev/null; then
        fuser -k "${port}/tcp" &>/dev/null || true
    fi
}

# Function: Check if port is in use
is_port_in_use() {
    local port=$1
    if command -v netstat &>/dev/null; then
        netstat -ano 2>/dev/null | grep -qE "LISTENING.*:$port|:$port.*LISTENING"
        return $?
    elif command -v lsof &>/dev/null; then
        lsof -i :"$port" &>/dev/null
        return $?
    fi
    return 1
}

# Function: Start Backend
start_backend() {
    echo -e "\n${CYAN}--------------------------------------------------${RESET}"
    echo -e "${BOLD}Starting Backend Server (FastAPI :8000)...${RESET}"
    echo -e "${CYAN}--------------------------------------------------${RESET}"

    if is_port_in_use 8000; then
        echo -e "${YELLOW}Port 8000 is already in use! Stopping previous instance...${RESET}"
        kill_port 8000
        sleep 1
    fi

    echo "Using Python: $PYTHON_BIN"
    nohup "$PYTHON_BIN" -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload > "$BACKEND_LOG" 2>&1 &
    local b_pid=$!
    echo "$b_pid" > "$BACKEND_PID_FILE"

    echo -e "Waiting for backend to initialize..."
    sleep 2

    if is_port_in_use 8000; then
        echo -e "${GREEN}✓ Backend successfully started!${RESET}"
        echo -e "  URL:  ${BOLD}http://127.0.0.1:8000${RESET}"
        echo -e "  Docs: ${BOLD}http://127.0.0.1:8000/docs${RESET}"
        echo -e "  Logs: ${CYAN}$BACKEND_LOG${RESET}"
    else
        echo -e "${RED}✗ Backend failed to start. Check logs:${RESET}"
        tail -n 10 "$BACKEND_LOG"
    fi
}

# Function: Start Frontend
start_frontend() {
    echo -e "\n${CYAN}--------------------------------------------------${RESET}"
    echo -e "${BOLD}Starting Frontend Server (Vite React :5173)...${RESET}"
    echo -e "${CYAN}--------------------------------------------------${RESET}"

    if is_port_in_use 5173; then
        echo -e "${YELLOW}Port 5173 is already in use! Stopping previous instance...${RESET}"
        kill_port 5173
        sleep 1
    fi

    if ! command -v npm &>/dev/null; then
        echo -e "${RED}Error: npm is not found in PATH!${RESET}"
        return 1
    fi

    (cd apps/web && npm run dev) > "$FRONTEND_LOG" 2>&1 &
    local f_pid=$!
    echo "$f_pid" > "$FRONTEND_PID_FILE"

    echo -e "Waiting for Vite to compile & launch..."
    sleep 3

    if is_port_in_use 5173; then
        echo -e "${GREEN}✓ Frontend successfully started!${RESET}"
        echo -e "  URL:  ${BOLD}http://localhost:5173${RESET}"
        echo -e "  Logs: ${CYAN}$FRONTEND_LOG${RESET}"
    else
        echo -e "${YELLOW}! Frontend is initializing. Check URL in a few seconds:${RESET}"
        echo -e "  URL:  ${BOLD}http://localhost:5173${RESET}"
        echo -e "  Logs: ${CYAN}$FRONTEND_LOG${RESET}"
    fi
}

# Function: Stop All
stop_all() {
    echo -e "\n${RED}--------------------------------------------------${RESET}"
    echo -e "${BOLD}Stopping All Running Servers & Freeing Ports...${RESET}"
    echo -e "${RED}--------------------------------------------------${RESET}"

    # Kill stored PIDs if present
    if [ -f "$BACKEND_PID_FILE" ]; then
        local b_pid
        b_pid=$(cat "$BACKEND_PID_FILE" 2>/dev/null)
        if [ -n "$b_pid" ]; then
            kill "$b_pid" &>/dev/null || taskkill //F //PID "$b_pid" &>/dev/null || true
        fi
        rm -f "$BACKEND_PID_FILE"
    fi

    if [ -f "$FRONTEND_PID_FILE" ]; then
        local f_pid
        f_pid=$(cat "$FRONTEND_PID_FILE" 2>/dev/null)
        if [ -n "$f_pid" ]; then
            kill "$f_pid" &>/dev/null || taskkill //F //PID "$f_pid" &>/dev/null || true
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi

    # Force kill any remaining processes on ports 8000 and 5173
    kill_port 8000
    kill_port 5173

    # On Windows, kill any orphaned uvicorn or vite node processes if requested
    echo -e "${GREEN}✓ All previous servers stopped! Ports 8000 and 5173 are free.${RESET}"
}

# Function: Status Check
check_status() {
    echo -e "\n${BLUE}==================================================${RESET}"
    echo -e "${BOLD}SERVER STATUS CHECK${RESET}"
    echo -e "${BLUE}==================================================${RESET}"

    # Backend
    if is_port_in_use 8000; then
        echo -e "  Backend (FastAPI) : ${GREEN}● RUNNING${RESET} on http://127.0.0.1:8000"
    else
        echo -e "  Backend (FastAPI) : ${RED}○ STOPPED${RESET} (Port 8000 free)"
    fi

    # Frontend
    if is_port_in_use 5173; then
        echo -e "  Frontend (Vite)   : ${GREEN}● RUNNING${RESET} on http://localhost:5173"
    else
        echo -e "  Frontend (Vite)   : ${RED}○ STOPPED${RESET} (Port 5173 free)"
    fi
    echo -e "${BLUE}==================================================${RESET}\n"
}

# Function: View Logs
view_backend_logs() {
    echo -e "\n${CYAN}--- Last 25 lines of Backend Logs ($BACKEND_LOG) ---${RESET}"
    if [ -f "$BACKEND_LOG" ]; then
        tail -n 25 "$BACKEND_LOG"
    else
        echo "No backend logs found."
    fi
    echo -e "${CYAN}-------------------------------------------------------${RESET}\n"
}

view_frontend_logs() {
    echo -e "\n${CYAN}--- Last 25 lines of Frontend Logs ($FRONTEND_LOG) ---${RESET}"
    if [ -f "$FRONTEND_LOG" ]; then
        tail -n 25 "$FRONTEND_LOG"
    else
        echo "No frontend logs found."
    fi
    echo -e "${CYAN}--------------------------------------------------------${RESET}\n"
}

# ==============================================================================
# Interactive Menu Loop
# ==============================================================================
show_menu() {
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${CYAN}║         CODENTER AI SDR - SERVER CONTROL         ║${RESET}"
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════╝${RESET}"
    echo -e "  ${GREEN}1)${RESET} ${BOLD}Start Both Servers${RESET} (Backend + Frontend)"
    echo -e "  ${GREEN}2)${RESET} Start Backend Only (FastAPI :8000)"
    echo -e "  ${GREEN}3)${RESET} Start Frontend Only (Vite React :5173)"
    echo -e "  ${YELLOW}4)${RESET} ${BOLD}Stop All Servers${RESET} (Free ports 8000 & 5173)"
    echo -e "  ${BLUE}5)${RESET} Restart Both Servers"
    echo -e "  ${CYAN}6)${RESET} Check Server Status"
    echo -e "  ${BOLD}7)${RESET} View Backend Logs"
    echo -e "  ${BOLD}8)${RESET} View Frontend Logs"
    echo -e "  ${RED}0)${RESET} Exit"
    echo -e "${CYAN}──────────────────────────────────────────────────${RESET}"
}

# If arguments were passed from CLI (non-interactive mode)
if [ "$1" = "start" ]; then
    start_backend
    start_frontend
    exit 0
elif [ "$1" = "stop" ]; then
    stop_all
    exit 0
elif [ "$1" = "restart" ]; then
    stop_all
    sleep 1
    start_backend
    start_frontend
    exit 0
elif [ "$1" = "status" ]; then
    check_status
    exit 0
fi

# Main Interactive Loop
while true; do
    show_menu
    read -rp "Select an option [0-8]: " choice
    case $choice in
        1)
            start_backend
            start_frontend
            echo ""
            ;;
        2)
            start_backend
            echo ""
            ;;
        3)
            start_frontend
            echo ""
            ;;
        4)
            stop_all
            echo ""
            ;;
        5)
            stop_all
            sleep 1
            start_backend
            start_frontend
            echo ""
            ;;
        6)
            check_status
            ;;
        7)
            view_backend_logs
            ;;
        8)
            view_frontend_logs
            ;;
        0)
            echo -e "${GREEN}Exiting. Have a great day!${RESET}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option! Please enter a number between 0 and 8.${RESET}\n"
            ;;
    esac
done
