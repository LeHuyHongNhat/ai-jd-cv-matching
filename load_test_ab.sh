#!/bin/bash

# Load Testing Script sử dụng Apache Bench (ab)
# Cần cài đặt apache2-utils (Linux) hoặc httpd (Mac)
# 
# Linux: sudo apt-get install apache2-utils
# Mac: brew install httpd

echo "=========================================="
echo "CV-JD MATCHING API - LOAD TEST (Apache Bench)"
echo "=========================================="
echo ""

# Kiểm tra xem ab đã được cài đặt chưa
if ! command -v ab &> /dev/null
then
    echo "❌ ERROR: Apache Bench (ab) chưa được cài đặt!"
    echo ""
    echo "Cài đặt:"
    echo "  Linux: sudo apt-get install apache2-utils"
    echo "  Mac: brew install httpd"
    echo "  Windows: Sử dụng WSL hoặc Docker"
    exit 1
fi

echo "✅ Apache Bench is installed"
echo ""

# Base URL
BASE_URL="http://localhost:8000"

# Kiểm tra server có đang chạy không
echo "Checking server status..."
if curl -s -f "${BASE_URL}/" > /dev/null 2>&1; then
    echo "✅ Server is running"
else
    echo "❌ ERROR: Server is not running!"
    echo "Please start the server first: uvicorn app.api.main:app --reload"
    exit 1
fi
echo ""

# Function để chạy test với ab
run_ab_test() {
    local test_name=$1
    local endpoint=$2
    local num_requests=$3
    local concurrency=$4
    local method=${5:-GET}
    local data_file=${6:-}
    
    echo "=========================================="
    echo "Test: $test_name"
    echo "=========================================="
    echo "Endpoint: $endpoint"
    echo "Total Requests: $num_requests"
    echo "Concurrency: $concurrency"
    echo "Method: $method"
    echo ""
    
    if [ -z "$data_file" ]; then
        # GET request
        ab -n "$num_requests" -c "$concurrency" -g "ab_results_${test_name// /_}.tsv" "${BASE_URL}${endpoint}"
    else
        # POST request với data
        ab -n "$num_requests" -c "$concurrency" -p "$data_file" -T "application/json" \
           -g "ab_results_${test_name// /_}.tsv" "${BASE_URL}${endpoint}"
    fi
    
    echo ""
    echo "Results saved to: ab_results_${test_name// /_}.tsv"
    echo ""
}

# Tạo file data cho POST request
cat > /tmp/jd_data.json <<EOF
{
    "text": "Job Title: Python Developer\nRequirements:\n- 3+ years Python experience\n- FastAPI, Django knowledge\n- REST API development\nSkills: Python, FastAPI, PostgreSQL, Docker"
}
EOF

echo "=========================================="
echo "MENU: Choose Test Scenario"
echo "=========================================="
echo "1. Light Load - Root Endpoint (100 requests, 10 concurrent)"
echo "2. Medium Load - Root Endpoint (500 requests, 25 concurrent)"
echo "3. Heavy Load - Root Endpoint (1000 requests, 50 concurrent)"
echo "4. Extreme Load - Root Endpoint (5000 requests, 100 concurrent)"
echo "5. Process JD - Light Load (50 requests, 5 concurrent)"
echo "6. Process JD - Medium Load (100 requests, 10 concurrent)"
echo "7. Run All Tests"
echo "0. Exit"
echo ""

read -p "Choose scenario (0-7): " choice

case $choice in
    1)
        run_ab_test "Light Load Root" "/" 100 10
        ;;
    2)
        run_ab_test "Medium Load Root" "/" 500 25
        ;;
    3)
        run_ab_test "Heavy Load Root" "/" 1000 50
        ;;
    4)
        run_ab_test "Extreme Load Root" "/" 5000 100
        ;;
    5)
        run_ab_test "Light Load Process JD" "/process/jd" 50 5 POST /tmp/jd_data.json
        ;;
    6)
        run_ab_test "Medium Load Process JD" "/process/jd" 100 10 POST /tmp/jd_data.json
        ;;
    7)
        echo "Running all tests..."
        echo ""
        run_ab_test "Warmup" "/" 50 5
        sleep 2
        run_ab_test "Light Load Root" "/" 100 10
        sleep 2
        run_ab_test "Medium Load Root" "/" 500 25
        sleep 2
        run_ab_test "Heavy Load Root" "/" 1000 50
        sleep 2
        run_ab_test "Light Load Process JD" "/process/jd" 50 5 POST /tmp/jd_data.json
        sleep 2
        run_ab_test "Medium Load Process JD" "/process/jd" 100 10 POST /tmp/jd_data.json
        ;;
    0)
        echo "Exiting..."
        rm -f /tmp/jd_data.json
        exit 0
        ;;
    *)
        echo "Invalid choice!"
        rm -f /tmp/jd_data.json
        exit 1
        ;;
esac

# Cleanup
rm -f /tmp/jd_data.json

echo ""
echo "=========================================="
echo "LOAD TEST COMPLETED"
echo "=========================================="
echo ""
echo "View results:"
echo "  - TSV files: ab_results_*.tsv"
echo "  - You can import these into Excel or plot with gnuplot"
echo ""

