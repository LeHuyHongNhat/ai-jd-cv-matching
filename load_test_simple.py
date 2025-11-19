"""
Load Testing Script đơn giản sử dụng concurrent.futures

Không cần cài thêm thư viện, chỉ cần Python standard library + requests

Chạy test:
    python load_test_simple.py
"""

import time
import requests
import concurrent.futures
import statistics
from typing import List, Dict, Any
from datetime import datetime


class LoadTester:
    """Simple Load Tester cho API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[Dict[str, Any]] = []
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Thực hiện một request và ghi nhận kết quả
        """
        start_time = time.time()
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, **kwargs)
            elif method == "POST":
                response = requests.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            elapsed = time.time() - start_time
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "elapsed": elapsed,
                "endpoint": endpoint,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "success": False,
                "status_code": 0,
                "elapsed": elapsed,
                "endpoint": endpoint,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def test_root_endpoint(self) -> Dict[str, Any]:
        """Test GET / endpoint"""
        return self.make_request("GET", "/")
    
    def test_process_jd(self) -> Dict[str, Any]:
        """Test POST /process/jd endpoint"""
        payload = {
            "text": """
            Job Title: Python Developer
            Requirements:
            - 3+ years Python experience
            - FastAPI, Django knowledge
            - REST API development
            Skills: Python, FastAPI, PostgreSQL, Docker
            """
        }
        return self.make_request("POST", "/process/jd", json=payload)
    
    def run_concurrent_test(
        self,
        num_requests: int = 100,
        num_workers: int = 10,
        test_function = None
    ):
        """
        Chạy test với nhiều request đồng thời
        
        Args:
            num_requests: Tổng số request cần gửi
            num_workers: Số lượng worker đồng thời (concurrent users)
            test_function: Hàm test cần chạy
        """
        print(f"\n{'='*60}")
        print(f"Running Load Test: {test_function.__name__}")
        print(f"Total Requests: {num_requests}")
        print(f"Concurrent Workers: {num_workers}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(test_function) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        self.results.extend(results)
        self.print_statistics(results, total_time)
    
    def print_statistics(self, results: List[Dict[str, Any]], total_time: float):
        """In ra thống kê kết quả test"""
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        
        response_times = [r["elapsed"] * 1000 for r in results]  # Convert to ms
        
        print(f"\n{'='*60}")
        print("Test Results:")
        print(f"{'='*60}")
        print(f"Total Requests:       {len(results)}")
        print(f"Successful:           {len(successful)} ({len(successful)/len(results)*100:.1f}%)")
        print(f"Failed:               {len(failed)} ({len(failed)/len(results)*100:.1f}%)")
        print(f"Total Time:           {total_time:.2f}s")
        print(f"Requests/Second:      {len(results)/total_time:.2f}")
        print(f"\nResponse Time Statistics (ms):")
        print(f"  Min:                {min(response_times):.2f}")
        print(f"  Max:                {max(response_times):.2f}")
        print(f"  Mean:               {statistics.mean(response_times):.2f}")
        print(f"  Median:             {statistics.median(response_times):.2f}")
        if len(response_times) > 1:
            print(f"  Std Dev:            {statistics.stdev(response_times):.2f}")
        
        # Percentiles
        sorted_times = sorted(response_times)
        p50 = sorted_times[int(len(sorted_times) * 0.50)]
        p75 = sorted_times[int(len(sorted_times) * 0.75)]
        p90 = sorted_times[int(len(sorted_times) * 0.90)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        
        print(f"\nPercentiles (ms):")
        print(f"  50th percentile:    {p50:.2f}")
        print(f"  75th percentile:    {p75:.2f}")
        print(f"  90th percentile:    {p90:.2f}")
        print(f"  95th percentile:    {p95:.2f}")
        print(f"  99th percentile:    {p99:.2f}")
        print(f"{'='*60}\n")
        
        if failed:
            print(f"\nFailed Requests Sample (first 5):")
            for i, fail in enumerate(failed[:5]):
                print(f"  {i+1}. Status: {fail['status_code']}, Error: {fail.get('error', 'N/A')}")
            print()


def main():
    """Main function để chạy load test"""
    
    # Khởi tạo tester
    tester = LoadTester(base_url="http://localhost:8000")
    
    print("\n" + "="*60)
    print("CV-JD MATCHING API - LOAD TEST")
    print("="*60)
    
    # Kiểm tra server có đang chạy không
    try:
        response = requests.get(f"{tester.base_url}/")
        if response.status_code != 200:
            print("\n❌ ERROR: API server không phản hồi đúng!")
            print("Vui lòng khởi động server trước: uvicorn app.api.main:app --reload")
            return
    except Exception as e:
        print(f"\n❌ ERROR: Không thể kết nối đến API server!")
        print(f"Error: {str(e)}")
        print("\nVui lòng khởi động server trước: uvicorn app.api.main:app --reload")
        return
    
    print("✅ Server is running\n")
    
    # Test scenarios
    scenarios = [
        {
            "name": "Warmup - Root Endpoint",
            "function": tester.test_root_endpoint,
            "requests": 50,
            "workers": 5
        },
        {
            "name": "Light Load - Root Endpoint",
            "function": tester.test_root_endpoint,
            "requests": 100,
            "workers": 10
        },
        {
            "name": "Medium Load - Root Endpoint",
            "function": tester.test_root_endpoint,
            "requests": 500,
            "workers": 25
        },
        {
            "name": "Heavy Load - Root Endpoint",
            "function": tester.test_root_endpoint,
            "requests": 1000,
            "workers": 50
        },
        {
            "name": "Process JD - Light Load",
            "function": tester.test_process_jd,
            "requests": 50,
            "workers": 5
        },
        {
            "name": "Process JD - Medium Load",
            "function": tester.test_process_jd,
            "requests": 100,
            "workers": 10
        }
    ]
    
    # Hỏi người dùng muốn chạy scenario nào
    print("Available Test Scenarios:")
    for i, scenario in enumerate(scenarios):
        print(f"  {i+1}. {scenario['name']} - {scenario['requests']} requests, {scenario['workers']} concurrent workers")
    
    print(f"  {len(scenarios)+1}. Run ALL scenarios")
    print(f"  0. Exit")
    
    try:
        choice = int(input("\nChọn scenario (0-{}): ".format(len(scenarios)+1)))
        
        if choice == 0:
            print("Exiting...")
            return
        elif choice == len(scenarios) + 1:
            # Chạy tất cả scenarios
            for scenario in scenarios:
                tester.run_concurrent_test(
                    num_requests=scenario["requests"],
                    num_workers=scenario["workers"],
                    test_function=scenario["function"]
                )
                time.sleep(2)  # Nghỉ 2 giây giữa các test
        elif 1 <= choice <= len(scenarios):
            scenario = scenarios[choice - 1]
            tester.run_concurrent_test(
                num_requests=scenario["requests"],
                num_workers=scenario["workers"],
                test_function=scenario["function"]
            )
        else:
            print("Invalid choice!")
    except ValueError:
        print("Invalid input!")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user!")
    
    print("\n" + "="*60)
    print("LOAD TEST COMPLETED")
    print("="*60)


if __name__ == "__main__":
    main()

