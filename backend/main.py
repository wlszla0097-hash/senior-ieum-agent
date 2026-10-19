"""main.py — FastAPI 앱의 시작점: 앱 생성, CORS 허용 도메인 설정, 라우터(창구) 6개 연결, 상태 확인(GET /).
실행: uvicorn main:app --reload  →  http://localhost:8000/docs 에서 Swagger 확인
"""
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()  # .env 파일의 환경 변수를 읽어 온다 (배포 환경에서는 대시보드 값이 우선)

from routers import data, conversations, chat, programs, employees, labor  # noqa: E402  (load_dotenv 뒤에 import)

app = FastAPI(
    title="시니어 이음 AI 비서 (Senior_ieum Agent)",
    description="시니어인턴십·선택근무제 운영 담당자를 위한 교육·컨설팅 AI 비서. "
                "출근 기록 시계열 요약을 시스템 프롬프트에 주입해 '우리 기관 상황을 아는' 답변을 만든다.",
    version="1.0.0",
)

# CORS: 프론트(Vercel) 도메인에서 이 API를 호출할 수 있게 허용한다.
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(programs.router)
app.include_router(employees.router)
app.include_router(labor.router)


@app.get("/", tags=["health"])
def root():
    """서버 생존 확인 + 현재 저장소/AI 설정 상태 (키 값은 절대 노출하지 않음)."""
    from services import db, ai
    return {
        "ok": True,
        "storage": db.backend_name(),
        "ai": "configured" if ai.is_configured() else "not configured",
        "docs": "/docs",
    }
