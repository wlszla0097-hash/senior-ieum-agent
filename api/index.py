"""Vercel 용 입구 — Render 와 같은 FastAPI 앱을 그대로 가져온다. (코드 공유, 배포처만 다름)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from main import app  # noqa: E402,F401
