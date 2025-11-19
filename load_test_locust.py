"""
Load Testing Script cho CV-JD Matching API sử dụng Locust

Cài đặt:
    pip install locust

Chạy test:
    locust -f load_test_locust.py --host=http://localhost:8000
    
Sau đó mở trình duyệt: http://localhost:8089
"""

import os
import random
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner

# Danh sách CV IDs và JD IDs để test (sẽ được cập nhật trong quá trình test)
cv_ids = []
jd_ids = []

# Sample JD text
SAMPLE_JD_TEXT = """
Job Title: Senior AI Engineer

Requirements:
- 5+ years of experience in Machine Learning and AI
- Strong Python programming skills
- Experience with Deep Learning frameworks (TensorFlow, PyTorch)
- Knowledge of NLP and Computer Vision
- Experience with cloud platforms (AWS, GCP, Azure)

Skills Required:
- Python, TensorFlow, PyTorch, Docker, Kubernetes
- Machine Learning, Deep Learning, NLP
- AWS, GCP, REST API

Education:
- Bachelor's or Master's degree in Computer Science, AI, or related field
"""


class CVJDMatchingUser(HttpUser):
    """
    Mô phỏng người dùng sử dụng CV-JD Matching API
    
    Thời gian chờ giữa các request: 1-3 giây
    """
    wait_time = between(1, 3)
    
    def on_start(self):
        """Được gọi khi user bắt đầu - có thể dùng để setup"""
        pass
    
    @task(1)
    def test_root_endpoint(self):
        """
        Test endpoint root - weight = 1 (10% traffic)
        """
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(3)
    def test_process_jd(self):
        """
        Test xử lý Job Description - weight = 3 (30% traffic)
        """
        payload = {
            "text": SAMPLE_JD_TEXT
        }
        
        with self.client.post(
            "/process/jd",
            json=payload,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    jd_id = data.get("doc_id")
                    if jd_id and jd_id not in jd_ids:
                        jd_ids.append(jd_id)
                    response.success()
                except Exception as e:
                    response.failure(f"Failed to parse response: {str(e)}")
            else:
                response.failure(f"Failed with status {response.status_code}")
    
    @task(3)
    def test_process_cv_simulation(self):
        """
        Test xử lý CV - weight = 3 (30% traffic)
        
        Lưu ý: Endpoint này yêu cầu upload file, nên ở đây chỉ mô phỏng
        Trong thực tế cần chuẩn bị file CV mẫu
        """
        # Mô phỏng upload file CV
        # Trong thực tế, bạn cần có file CV thật trong thư mục
        cv_file_path = "input\cvs\[PTIT] CV AI Engineer - Le Huy Hong Nhat.pdf"
        
        if os.path.exists(cv_file_path):
            with open(cv_file_path, 'rb') as f:
                files = {'file': ('cv_sample.pdf', f, 'application/pdf')}
                with self.client.post(
                    "/process/cv",
                    files=files,
                    catch_response=True
                ) as response:
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            cv_id = data.get("doc_id")
                            if cv_id and cv_id not in cv_ids:
                                cv_ids.append(cv_id)
                            response.success()
                        except Exception as e:
                            response.failure(f"Failed to parse response: {str(e)}")
                    else:
                        response.failure(f"Failed with status {response.status_code}")
        else:
            # Skip nếu không có file
            pass
    
    @task(3)
    def test_match_cv_jd(self):
        """
        Test matching CV và JD - weight = 3 (30% traffic)
        """
        # Chỉ test nếu đã có cv_id và jd_id
        if cv_ids and jd_ids:
            cv_id = random.choice(cv_ids)
            jd_id = random.choice(jd_ids)
            
            with self.client.get(
                f"/match/{cv_id}/{jd_id}",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                elif response.status_code == 404:
                    response.failure("CV or JD not found")
                else:
                    response.failure(f"Failed with status {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Được gọi khi test bắt đầu
    """
    print("=" * 60)
    print("LOAD TEST STARTING")
    print("=" * 60)
    print("Test Configuration:")
    print(f"  Host: {environment.host}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Được gọi khi test kết thúc
    """
    print("=" * 60)
    print("LOAD TEST COMPLETED")
    print("=" * 60)
    print(f"Total CV IDs collected: {len(cv_ids)}")
    print(f"Total JD IDs collected: {len(jd_ids)}")
    print("=" * 60)
    
    # In ra stats summary
    stats = environment.stats
    print("\nRequest Statistics:")
    print(f"  Total Requests: {stats.total.num_requests}")
    print(f"  Total Failures: {stats.total.num_failures}")
    print(f"  Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"  Min Response Time: {stats.total.min_response_time:.2f}ms")
    print(f"  Max Response Time: {stats.total.max_response_time:.2f}ms")
    print(f"  Requests per Second: {stats.total.total_rps:.2f}")
    print("=" * 60)

