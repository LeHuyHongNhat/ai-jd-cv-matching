"""Pytest configuration và shared fixtures"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch
from dotenv import load_dotenv


def load_env_file():
    """Load environment variables từ config.env hoặc .env"""
    # Fix cứng đường dẫn file config.env
    config_env_path = Path(r"D:\Python Projects\GP\config.env")
    
    # Nếu file không tồn tại ở đường dẫn cứng, thử tìm ở thư mục hiện tại
    if not config_env_path.exists():
        # Lấy thư mục root của project (parent của tests/)
        root_dir = Path(__file__).parent.parent
        config_env_path = root_dir / "config.env"
    
    # Thử load từ config.env
    if config_env_path.exists() and config_env_path.is_file():
        load_dotenv(dotenv_path=config_env_path, override=True)
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if api_key and api_key.startswith("sk-"):
            # Đã load được API key hợp lệ
            return
    
    # Sau đó thử load từ .env
    env_path = Path(r"D:\Python Projects\GP\.env")
    if not env_path.exists():
        root_dir = Path(__file__).parent.parent
        env_path = root_dir / ".env"
    
    if env_path.exists() and env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=True)
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if api_key and api_key.startswith("sk-"):
            return


@pytest.fixture(autouse=True)
def setup_env():
    """Setup environment variables cho testing"""
    # Load từ file config.env hoặc .env trước
    load_env_file()
    
    # Chỉ mock OpenAI API key nếu chưa có trong environment (sau khi load file)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "" or api_key == "test-key-for-mocking":
        os.environ["OPENAI_API_KEY"] = "test-key-for-mocking"
    yield
    # Cleanup nếu cần
