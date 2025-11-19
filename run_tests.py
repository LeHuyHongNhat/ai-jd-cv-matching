"""
Script để chạy tất cả tests
"""
import subprocess
import sys


def run_tests():
    """Chạy pytest với các options"""
    cmd = [
        sys.executable,
        "-m", "pytest",
        "tests/",
        "-v",  # Verbose
        "--tb=short",  # Short traceback format
        "-x",  # Stop on first failure (có thể bỏ nếu muốn chạy hết)
    ]
    
    print("Bat dau chay tests...")
    print(f"Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n[SUCCESS] Tat ca tests da pass!")
    else:
        print("\n[FAILED] Mot so tests da fail. Kiem tra output o tren.")
    
    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)

