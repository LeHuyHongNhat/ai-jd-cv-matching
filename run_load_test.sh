#!/bin/bash

# Load Testing Script cho Linux/Mac
# 
# Usage: ./run_load_test.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "CV-JD MATCHING API - LOAD TEST"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null
then
    echo -e "${RED}❌ ERROR: Python is not installed!${NC}"
    echo "Please install Python first: https://www.python.org/downloads/"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo -e "${GREEN}✅ Python is installed${NC}"
echo ""

# Function to check if a Python package is installed
check_package() {
    $PYTHON_CMD -c "import $1" 2>/dev/null
    return $?
}

# Function to install package
install_package() {
    echo "Installing $1..."
    $PYTHON_CMD -m pip install "$1"
}

# Menu
show_menu() {
    echo "Choose Load Testing Method:"
    echo ""
    echo "1. Locust (Web UI) - Recommended"
    echo "2. Locust (Headless - No UI)"
    echo "3. Simple Load Test (Interactive)"
    echo "4. Install Load Testing Dependencies"
    echo "5. Start API Server (in background)"
    echo "6. Stop API Server"
    echo "7. Apache Bench Test (if available)"
    echo "0. Exit"
    echo ""
}

# Check server status
check_server() {
    if curl -s -f http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server is running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Server is not running${NC}"
        return 1
    fi
}

# Start server
start_server() {
    echo ""
    echo "========================================"
    echo "Starting API Server"
    echo "========================================"
    echo ""
    
    # Check if uvicorn is installed
    if ! check_package uvicorn; then
        echo -e "${YELLOW}uvicorn not installed, installing...${NC}"
        install_package uvicorn
    fi
    
    # Check if server is already running
    if check_server; then
        echo "Server is already running!"
        return
    fi
    
    echo "Starting server in background..."
    nohup $PYTHON_CMD -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
    SERVER_PID=$!
    echo $SERVER_PID > server.pid
    
    # Wait a bit for server to start
    sleep 3
    
    if check_server; then
        echo -e "${GREEN}✅ Server started successfully!${NC}"
        echo "PID: $SERVER_PID"
        echo "Logs: tail -f server.log"
    else
        echo -e "${RED}❌ Failed to start server${NC}"
        echo "Check server.log for details"
    fi
}

# Stop server
stop_server() {
    echo ""
    echo "========================================"
    echo "Stopping API Server"
    echo "========================================"
    echo ""
    
    if [ -f server.pid ]; then
        PID=$(cat server.pid)
        if ps -p $PID > /dev/null; then
            echo "Stopping server (PID: $PID)..."
            kill $PID
            rm server.pid
            echo -e "${GREEN}✅ Server stopped${NC}"
        else
            echo "Server is not running"
            rm server.pid
        fi
    else
        echo "No PID file found. Trying to find uvicorn process..."
        pkill -f "uvicorn app.api.main:app"
        echo "Done"
    fi
}

# Locust Web UI
run_locust_web() {
    echo ""
    echo "========================================"
    echo "Starting Locust with Web UI"
    echo "========================================"
    echo ""
    
    # Check if locust is installed
    if ! check_package locust; then
        echo -e "${YELLOW}Locust not installed, installing...${NC}"
        install_package locust
    fi
    
    echo "Locust will start on http://localhost:8089"
    echo ""
    echo "Configuration:"
    echo "  - Number of users: How many concurrent users to simulate"
    echo "  - Spawn rate: How many users to add per second"
    echo "  - Host: http://localhost:8000"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""
    
    read -p "Press Enter to start..."
    
    locust -f load_test_locust.py --host=http://localhost:8000
}

# Locust Headless
run_locust_headless() {
    echo ""
    echo "========================================"
    echo "Locust Headless Mode"
    echo "========================================"
    echo ""
    
    # Check if locust is installed
    if ! check_package locust; then
        echo -e "${YELLOW}Locust not installed, installing...${NC}"
        install_package locust
    fi
    
    read -p "Number of users (default 100): " users
    users=${users:-100}
    
    read -p "Spawn rate (users/sec, default 10): " spawn_rate
    spawn_rate=${spawn_rate:-10}
    
    read -p "Run time (e.g. 60s, 5m, default 60s): " runtime
    runtime=${runtime:-60s}
    
    echo ""
    echo "Running test with:"
    echo "  Users: $users"
    echo "  Spawn rate: $spawn_rate users/sec"
    echo "  Run time: $runtime"
    echo ""
    
    read -p "Press Enter to start..."
    
    timestamp=$(date +%Y%m%d_%H%M%S)
    report_file="load_test_report_${timestamp}.html"
    
    locust -f load_test_locust.py --host=http://localhost:8000 \
        --users $users --spawn-rate $spawn_rate --run-time $runtime \
        --headless --html=$report_file
    
    echo ""
    echo "========================================"
    echo "Test completed!"
    echo "Report saved to: $report_file"
    echo "========================================"
}

# Simple Load Test
run_simple_test() {
    echo ""
    echo "========================================"
    echo "Simple Load Test (Interactive)"
    echo "========================================"
    echo ""
    
    # Check if requests is installed
    if ! check_package requests; then
        echo -e "${YELLOW}requests not installed, installing...${NC}"
        install_package requests
    fi
    
    $PYTHON_CMD load_test_simple.py
}

# Install dependencies
install_dependencies() {
    echo ""
    echo "========================================"
    echo "Installing Load Testing Dependencies"
    echo "========================================"
    echo ""
    
    if [ -f requirements_loadtest.txt ]; then
        echo "Installing from requirements_loadtest.txt..."
        $PYTHON_CMD -m pip install -r requirements_loadtest.txt
        echo ""
        echo "========================================"
        echo -e "${GREEN}✅ Installation completed!${NC}"
        echo "========================================"
    else
        echo "requirements_loadtest.txt not found!"
        echo "Installing essential packages..."
        install_package locust
        install_package requests
    fi
}

# Apache Bench test
run_apache_bench() {
    echo ""
    echo "========================================"
    echo "Apache Bench Test"
    echo "========================================"
    echo ""
    
    if ! command -v ab &> /dev/null; then
        echo -e "${RED}❌ Apache Bench (ab) is not installed!${NC}"
        echo ""
        echo "Install with:"
        echo "  Ubuntu/Debian: sudo apt-get install apache2-utils"
        echo "  Mac: brew install httpd"
        return 1
    fi
    
    if [ -f load_test_ab.sh ]; then
        chmod +x load_test_ab.sh
        ./load_test_ab.sh
    else
        echo "load_test_ab.sh not found!"
        echo ""
        echo "Running simple ab test..."
        read -p "Number of requests (default 1000): " requests
        requests=${requests:-1000}
        
        read -p "Concurrency (default 50): " concurrency
        concurrency=${concurrency:-50}
        
        echo ""
        echo "Running: ab -n $requests -c $concurrency http://localhost:8000/"
        echo ""
        
        ab -n $requests -c $concurrency http://localhost:8000/
    fi
}

# Main loop
while true; do
    show_menu
    check_server
    echo ""
    read -p "Enter your choice (0-7): " choice
    
    case $choice in
        1) run_locust_web ;;
        2) run_locust_headless ;;
        3) run_simple_test ;;
        4) install_dependencies ;;
        5) start_server ;;
        6) stop_server ;;
        7) run_apache_bench ;;
        0) 
            echo ""
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice!${NC}"
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    clear
done

