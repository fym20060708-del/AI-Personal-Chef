"""Paths shared by development and the portable Windows package."""
import os
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = Path(os.environ.get("PERSONAL_CHEF_HOME", APP_DIR.parent)).resolve()
load_dotenv(ROOT_DIR / ".env", override=True)
DATA_DIR = ROOT_DIR / "data"


def missing_settings():
    required = ("DASHSCOPE_BASE_URL", "DASHSCOPE_API_KEY", "DASHSCOPE_MODEL",
                "TAVILY_API_KEY", "OSS_ACCESS_KEY_ID", "OSS_ACCESS_KEY_SECRET",
                "OSS_BUCKET", "OSS_ENDPOINT", "OSS_REGION")
    return [name for name in required if not os.getenv(name, "").strip()
            or os.getenv(name, "").startswith("YOUR_")]
