# Quick Start - Load Testing

Hướng dẫn nhanh để bắt đầu Load Testing trong 5 phút.

## 🚀 Cách nhanh nhất (Khuyên dùng)

### Bước 1: Cài đặt dependencies

```bash
pip install locust requests
```

### Bước 2: Khởi động API Server

```bash
# Terminal 1: Start server
uvicorn app.api.main:app --reload
```

### Bước 3: Chạy Load Test

#### Option A: Locust với Web UI (Dễ nhất)

```bash
# Terminal 2: Start Locust
locust -f load_test_locust.py --host=http://localhost:8000

# Mở trình duyệt: http://localhost:8089
# - Number of users: 100
# - Spawn rate: 10
# - Click "Start swarming"
```

#### Option B: Simple Script (Không cần Web UI)

```bash
# Terminal 2: Run simple test
python load_test_simple.py

# Chọn scenario từ menu
```

#### Option C: Script tự động (Windows)

```bash
# Chạy file batch
run_load_test.bat
```

#### Option D: Script tự động (Linux/Mac)

```bash
# Chạy shell script
chmod +x run_load_test.sh
./run_load_test.sh
```

---

## 📊 Đọc kết quả

### Locust

Xem real-time trên Web UI tại `http://localhost:8089`

Các chỉ số quan trọng:

- **RPS** (Requests/s): Càng cao càng tốt (> 100 là tốt)
- **Response Time**: Trung bình nên < 1000ms
- **Failures**: Nên < 1%

### Khi nào cần lo?

- ❌ Error rate > 1%
- ❌ Response time > 3 seconds
- ❌ Server crash hoặc không phản hồi

---

## 🎯 Test Scenarios Mẫu

### 1. Smoke Test (Kiểm tra cơ bản)

```bash
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 10 --spawn-rate 5 --run-time 30s --headless
```

### 2. Load Test (Tải bình thường)

```bash
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 5m --headless
```

### 3. Stress Test (Tìm breaking point)

```bash
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 500 --spawn-rate 50 --run-time 10m --headless \
    --html=report.html
```

---

## 💡 Tips

1. **Bắt đầu nhỏ**: Test với 10-50 users trước
2. **Tăng dần**: 50 → 100 → 200 → 500 users
3. **Monitor**: Xem CPU/RAM trong khi test
4. **Lặp lại**: Test nhiều lần để có kết quả chính xác

---

## 📝 Export Report

```bash
# Export HTML report
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 5m \
    --headless --html=load_test_report.html

# Mở file: load_test_report.html
```

---

## 🆘 Troubleshooting

### Lỗi: Connection refused

```
✅ Giải pháp: Khởi động server trước
uvicorn app.api.main:app --reload
```

### Lỗi: Module not found

```
✅ Giải pháp: Cài đặt dependencies
pip install locust requests
```

### Server chậm/crash

```
✅ Giải pháp:
1. Giảm số concurrent users
2. Tăng resources (CPU/RAM)
3. Optimize code
```

---

## 📚 Đọc thêm

- Chi tiết: `LOAD_TESTING_README.md`
- Các phương pháp khác: Apache Bench, k6
- Phân tích kết quả: `python analyze_results.py`

---

## ⚡ One-liner Commands

```bash
# All-in-one: Cài + chạy + export report
pip install locust && \
locust -f load_test_locust.py --host=http://localhost:8000 \
    --users 100 --spawn-rate 10 --run-time 2m \
    --headless --html=report_$(date +%Y%m%d_%H%M%S).html
```

```bash
# Quick test với simple script
python load_test_simple.py
```

```bash
# Apache Bench (nếu đã cài)
ab -n 1000 -c 50 http://localhost:8000/
```

---

**Chúc bạn load testing thành công! 🎉**
