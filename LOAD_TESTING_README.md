# Load Testing cho CV-JD Matching API

Hướng dẫn chi tiết cách thực hiện Load Testing và Stress Testing cho hệ thống CV-JD Matching.

## Mục lục

- [Tổng quan](#tổng-quan)
- [Các phương pháp Load Testing](#các-phương-pháp-load-testing)
- [Chuẩn bị](#chuẩn-bị)
- [Phương pháp 1: Locust](#phương-pháp-1-locust-khuyên-dùng)
- [Phương pháp 2: Simple Load Test](#phương-pháp-2-simple-load-test)
- [Phương pháp 3: Apache Bench](#phương-pháp-3-apache-bench)
- [Phương pháp 4: k6](#phương-pháp-4-k6)
- [Đọc và phân tích kết quả](#đọc-và-phân-tích-kết-quả)
- [Best Practices](#best-practices)

---

## Tổng quan

Load Testing giúp bạn:

- **Xác định khả năng chịu tải**: Hệ thống có thể xử lý bao nhiêu request đồng thời?
- **Tìm bottleneck**: Phần nào của hệ thống bị nghẽn trước?
- **Đo performance**: Response time, throughput, error rate
- **Kiểm tra stability**: Hệ thống có ổn định khi chịu tải cao?

## Các phương pháp Load Testing

| Công cụ           | Độ khó     | Giao diện      | Tính năng                     | Khuyên dùng |
| ----------------- | ---------- | -------------- | ----------------------------- | ----------- |
| **Locust**        | Dễ         | ✅ Web UI      | Phân tán, real-time, flexible | ⭐⭐⭐⭐⭐  |
| **Simple Script** | Rất dễ     | ❌ Console     | Đơn giản, nhanh               | ⭐⭐⭐⭐    |
| **Apache Bench**  | Dễ         | ❌ Console     | Nhanh, lightweight            | ⭐⭐⭐      |
| **k6**            | Trung bình | ❌ Console     | Modern, nhiều tính năng       | ⭐⭐⭐⭐    |
| **JMeter**        | Khó        | ✅ Desktop GUI | Đầy đủ, enterprise            | ⭐⭐⭐      |

---

## Chuẩn bị

### 1. Khởi động API Server

Trước khi test, đảm bảo server đang chạy:

```bash
# Terminal 1: Khởi động server
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

Kiểm tra server:

```bash
curl http://localhost:8000/
```

### 2. Cài đặt Dependencies

```bash
# Cho Locust
pip install locust

# Cho Simple Load Test
pip install requests

# Cho Apache Bench (Linux)
sudo apt-get install apache2-utils

# Cho Apache Bench (Mac)
brew install httpd

# Cho k6 (Linux/Mac)
# Xem hướng dẫn tại: https://k6.io/docs/getting-started/installation/
```

---

## Phương pháp 1: Locust (Khuyên dùng)

### Ưu điểm

✅ Giao diện web đẹp, trực quan  
✅ Real-time charts và statistics  
✅ Dễ viết test scenarios bằng Python  
✅ Hỗ trợ distributed testing  
✅ Export reports (HTML, CSV)

### Cài đặt

```bash
pip install locust
```

### Chạy Test

#### Cách 1: Web Interface (Recommended)

```bash
# Chạy Locust với Web UI
locust -f load_test_locust.py --host=http://localhost:8000

# Mở trình duyệt: http://localhost:8089
```

Trong Web UI:

1. **Number of users**: Số lượng users đồng thời (vd: 100)
2. **Spawn rate**: Tốc độ tăng users/giây (vd: 10 users/s)
3. Click **Start swarming**

#### Cách 2: Headless (No UI)

```bash
# Test với 100 users, tăng 10 users/s, chạy trong 60s
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 60s --headless

# Export HTML report
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 60s --headless \
    --html=load_test_report.html
```

### Test Scenarios trong Locust

File `load_test_locust.py` bao gồm:

- ✅ **test_root_endpoint**: Test GET / (10% traffic)
- ✅ **test_process_jd**: Test POST /process/jd (30% traffic)
- ✅ **test_process_cv_simulation**: Test POST /process/cv (30% traffic)
- ✅ **test_match_cv_jd**: Test GET /match/{cv_id}/{jd_id} (30% traffic)

### Ví dụ Test Progressively

```bash
# Bước 1: Warmup - 10 users
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 10 --spawn-rate 5 --run-time 30s --headless

# Bước 2: Light Load - 50 users
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 50 --spawn-rate 10 --run-time 60s --headless

# Bước 3: Medium Load - 100 users
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 20 --run-time 120s --headless

# Bước 4: Heavy Load - 500 users
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 500 --spawn-rate 50 --run-time 300s --headless

# Bước 5: Stress Test - 1000 users
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 1000 --spawn-rate 100 --run-time 600s --headless
```

---

## Phương pháp 2: Simple Load Test

### Ưu điểm

✅ Không cần cài thêm thư viện đặc biệt  
✅ Code đơn giản, dễ customize  
✅ Statistics chi tiết (percentiles, std dev)  
✅ Interactive menu

### Chạy Test

```bash
python load_test_simple.py
```

Chọn scenario từ menu:

```
1. Warmup - Root Endpoint (50 requests, 5 workers)
2. Light Load - Root Endpoint (100 requests, 10 workers)
3. Medium Load - Root Endpoint (500 requests, 25 workers)
4. Heavy Load - Root Endpoint (1000 requests, 50 workers)
5. Process JD - Light Load (50 requests, 5 workers)
6. Process JD - Medium Load (100 requests, 10 workers)
7. Run ALL scenarios
```

### Customize Test

Mở file `load_test_simple.py` và thêm scenario mới:

```python
scenarios.append({
    "name": "Custom Test",
    "function": tester.test_root_endpoint,
    "requests": 2000,  # Tổng số requests
    "workers": 100     # Concurrent workers
})
```

---

## Phương pháp 3: Apache Bench

### Ưu điểm

✅ Rất nhanh và nhẹ  
✅ Có sẵn trên nhiều hệ điều hành  
✅ Dễ sử dụng

### Nhược điểm

❌ Chỉ test được 1 endpoint mỗi lần  
❌ Không có giao diện đẹp  
❌ Ít tính năng nâng cao

### Chạy Test

#### Linux/Mac:

```bash
chmod +x load_test_ab.sh
./load_test_ab.sh
```

#### Manual Commands:

```bash
# Test Root Endpoint - 1000 requests, 50 concurrent
ab -n 1000 -c 50 http://localhost:8000/

# Test với POST request
# Tạo file data
echo '{"text":"Job Description..."}' > jd_data.json

# Chạy test
ab -n 100 -c 10 -p jd_data.json -T application/json \
   http://localhost:8000/process/jd
```

---

## Phương pháp 4: k6

### Ưu điểm

✅ Modern, performance cao  
✅ Script bằng JavaScript  
✅ Nhiều tính năng nâng cao (thresholds, checks)  
✅ Cloud integration

### Cài đặt

```bash
# Mac
brew install k6

# Linux
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

### Script ví dụ

Tạo file `load_test_k6.js`:

```javascript
import http from "k6/http";
import { check, sleep } from "k6";

export let options = {
  stages: [
    { duration: "30s", target: 20 }, // Ramp up to 20 users
    { duration: "1m", target: 50 }, // Stay at 50 users
    { duration: "30s", target: 0 }, // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ["p(95)<500"], // 95% requests must complete below 500ms
    http_req_failed: ["rate<0.01"], // Error rate must be below 1%
  },
};

export default function () {
  // Test root endpoint
  let res = http.get("http://localhost:8000/");
  check(res, {
    "status is 200": (r) => r.status === 200,
    "response time < 500ms": (r) => r.timings.duration < 500,
  });

  sleep(1);

  // Test process JD
  let payload = JSON.stringify({
    text: "Job Title: Python Developer\nSkills: Python, FastAPI",
  });

  let params = {
    headers: { "Content-Type": "application/json" },
  };

  res = http.post("http://localhost:8000/process/jd", payload, params);
  check(res, {
    "JD processed successfully": (r) => r.status === 200,
  });

  sleep(1);
}
```

### Chạy k6 Test

```bash
# Chạy test
k6 run load_test_k6.js

# Chạy với nhiều users hơn
k6 run --vus 100 --duration 30s load_test_k6.js

# Export results
k6 run --out json=test_results.json load_test_k6.js
```

---

## Đọc và phân tích kết quả

### Các chỉ số quan trọng

#### 1. **Request per Second (RPS / Throughput)**

- Số lượng requests hệ thống xử lý được mỗi giây
- **Càng cao càng tốt**
- Ví dụ: 1000 RPS = hệ thống xử lý 1000 requests/giây

#### 2. **Response Time (Latency)**

- Thời gian từ khi gửi request đến khi nhận response
- **Càng thấp càng tốt**
- Quan tâm đến:
  - **Mean**: Trung bình
  - **Median (p50)**: 50% requests nhanh hơn giá trị này
  - **p95**: 95% requests nhanh hơn giá trị này
  - **p99**: 99% requests nhanh hơn giá trị này

#### 3. **Error Rate**

- Tỷ lệ requests bị lỗi
- **Nên < 1%**
- Phân loại lỗi:
  - 4xx: Client errors
  - 5xx: Server errors
  - Timeout

#### 4. **Concurrent Users**

- Số lượng users đồng thời hệ thống có thể handle
- Tìm "breaking point" - điểm mà error rate tăng đột ngột

### Ví dụ đọc kết quả Locust

```
Type     Name                    # reqs    # fails   Avg      Min      Max    Median   req/s
------------------------------------------------------------------------
GET      /                       10000     0(0.00%)  45       12       234    43       166.67
POST     /process/jd             5000      10(0.20%) 1250     500      3000   1200     83.33
GET      /match/{cv}/{jd}        3000      5(0.17%)  850      200      2500   800      50.00
------------------------------------------------------------------------
Total                            18000     15(0.08%) 715      12       3000   600      300.00

95%ile   99%ile
--------
120      180
2100     2800
1800     2300
--------
1500     2500
```

**Phân tích:**

- ✅ **RPS**: 300 requests/s - Khá tốt
- ✅ **Error Rate**: 0.08% - Rất thấp, tốt
- ⚠️ **Response Time**:
  - Root endpoint: Tốt (45ms trung bình)
  - Process JD: Chậm (1250ms) - Cần optimize
  - Match: Chấp nhận được (850ms)
- ⚠️ **p99**: 2500ms - Có một số requests rất chậm

### Khi nào cần lo ngại?

🚨 **Warning Signs:**

- Error rate > 1%
- p95 response time > 3 seconds
- Response time tăng đột ngột khi tăng load
- Memory leak (RAM tăng liên tục)
- CPU usage = 100% liên tục

---

## Best Practices

### 1. Test Progressively (Tăng dần)

```
Warmup (10 users) → Light (50 users) → Medium (100 users)
→ Heavy (500 users) → Stress (1000+ users)
```

**Mục đích**: Tìm breaking point mà không làm crash server ngay

### 2. Test các Scenarios khác nhau

- **Smoke Test**: 1-2 users, kiểm tra API hoạt động
- **Load Test**: Users bình thường, kiểm tra performance
- **Stress Test**: Vượt quá capacity, tìm breaking point
- **Spike Test**: Tăng đột ngột users, kiểm tra elasticity
- **Soak Test**: Chạy lâu (vài giờ), tìm memory leaks

### 3. Monitor hệ thống trong khi test

```bash
# CPU & Memory
htop

# API Server logs
tail -f logs/api.log

# Docker stats (nếu dùng Docker)
docker stats
```

### 4. Test trên môi trường giống Production

- Cùng hardware specs
- Cùng network latency
- Cùng database size
- Cùng cấu hình

### 5. Lặp lại tests

- Test nhiều lần để có kết quả chính xác
- Test vào các thời điểm khác nhau trong ngày
- So sánh kết quả sau mỗi lần optimize

---

## Tối ưu hóa dựa trên kết quả

### Nếu Response Time cao

1. **Profile code**: Tìm phần code chậm

   ```python
   import cProfile
   cProfile.run('your_function()')
   ```

2. **Optimize database queries**

   - Add indexes
   - Use caching (Redis)
   - Connection pooling

3. **Use async/await** (FastAPI đã support)

4. **Cache OpenAI responses** (nếu có requests giống nhau)

### Nếu RPS thấp

1. **Increase workers**

   ```bash
   uvicorn app.api.main:app --workers 4
   ```

2. **Use Gunicorn**

   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.api.main:app
   ```

3. **Horizontal scaling**: Deploy nhiều instances + Load Balancer

### Nếu Error Rate cao

1. **Check logs**: Xem lỗi gì xảy ra
2. **Add error handling**: Try-except, timeouts
3. **Add rate limiting**: Protect API khỏi abuse
4. **Scale infrastructure**: Tăng resources

---

## Ví dụ Full Test Flow

```bash
# Bước 1: Khởi động server
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Bước 2: Smoke test (kiểm tra cơ bản)
curl http://localhost:8000/

# Bước 3: Light load test với Locust
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 50 --spawn-rate 10 --run-time 60s --headless \
    --html=report_light.html

# Bước 4: Analyze kết quả, optimize nếu cần

# Bước 5: Medium load test
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 20 --run-time 120s --headless \
    --html=report_medium.html

# Bước 6: Heavy load test
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 500 --spawn-rate 50 --run-time 300s --headless \
    --html=report_heavy.html

# Bước 7: Stress test - tìm breaking point
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 1000 --spawn-rate 100 --run-time 600s --headless \
    --html=report_stress.html
```

---

## Troubleshooting

### Lỗi: Connection refused

```
❌ requests.exceptions.ConnectionError: ('Connection aborted.')
```

**Giải pháp**: Server chưa chạy, khởi động server trước

### Lỗi: Too many open files

```
❌ OSError: [Errno 24] Too many open files
```

**Giải pháp**: Tăng file descriptor limit

```bash
ulimit -n 10000
```

### Lỗi: OpenAI Rate Limit

```
❌ openai.error.RateLimitError: Rate limit exceeded
```

**Giải pháp**:

- Giảm số concurrent users
- Thêm retry logic
- Upgrade OpenAI tier

---

## Kết luận

Với 4 phương pháp trên, bạn có thể:

1. ✅ **Locust**: Best cho production testing, có UI đẹp
2. ✅ **Simple Script**: Best cho quick tests, dễ customize
3. ✅ **Apache Bench**: Best cho simple benchmarks
4. ✅ **k6**: Best cho CI/CD integration

**Khuyên dùng workflow:**

1. Bắt đầu với **Simple Script** để test nhanh
2. Dùng **Locust** cho comprehensive testing
3. Integrate **k6** vào CI/CD pipeline

**Mục tiêu:**

- Tìm ra hệ thống chịu được bao nhiêu concurrent users
- Identify bottlenecks
- Optimize và test lại
- Document results để reference sau này

---

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [k6 Documentation](https://k6.io/docs/)
- [Apache Bench Manual](https://httpd.apache.org/docs/2.4/programs/ab.html)
- [FastAPI Performance Tips](https://fastapi.tiangolo.com/deployment/concepts/)
