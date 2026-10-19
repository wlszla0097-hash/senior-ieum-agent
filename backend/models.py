"""models.py — Pydantic '신청서 양식': 요청 본문이 양식과 다르면 FastAPI가 422로 자동 거절한다.
(날짜 형식 오류, 음수 value, 너무 긴 memo 등은 라우터 코드에 닿기 전에 막힌다.)
"""
import datetime as dt
from typing import Literal, Optional
from pydantic import BaseModel, Field

Program = Literal["senior", "flexwork"]  # 시계열 데이터가 있는 사업 (data 컬렉션의 program 값)
ChatProgram = Literal["senior", "flexwork", "hr"]  # 채팅 탭: 사업 2개 + HR 공통 계산 (programs/registry.py 와 일치)
Mode = Literal["onboarding", "setup", "qa"]  # 비서 모드: 신규 담당자 온보딩 / 신규 기관 세팅 / 실무 Q&A
# 주의: 필드 이름 date 와 타입 이름이 겹치면 Optional[date] 가 깨지므로 타입은 dt.date 로 쓴다.


class DataIn(BaseModel):
    """시계열 데이터 1건: 특정 날짜·사업장의 출근 인원."""
    date: dt.date
    value: float = Field(ge=0, le=10000, description="출근 인원(명)")
    memo: str = Field(default="", max_length=300)
    program: Program = "senior"
    site: str = Field(default="(가상)A사", min_length=1, max_length=60, description="참여기업명 — 시연은 가명만")


class DataUpdate(BaseModel):
    """수정은 바꾸고 싶은 항목만 보낸다."""
    date: Optional[dt.date] = None
    value: Optional[float] = Field(default=None, ge=0, le=10000)
    memo: Optional[str] = Field(default=None, max_length=300)
    program: Optional[Program] = None
    site: Optional[str] = Field(default=None, min_length=1, max_length=60)


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(max_length=8000)


class ConversationIn(BaseModel):
    title: str = Field(default="새 대화", max_length=100)
    program: ChatProgram = "senior"
    mode: Mode = "qa"
    messages: list[Message] = []


class ChatIn(BaseModel):
    """채팅 요청. conversation_id가 있으면 그 대화에 이어서 저장한다."""
    message: str = Field(min_length=1, max_length=2000, pattern=r"\S")  # 공백만 있는 질문은 거절
    program: ChatProgram = "senior"
    mode: Mode = "qa"
    conversation_id: Optional[str] = None


class WageUpdate(BaseModel):
    """담당자가 계약 시급을 수정할 때 — 사유·수정자 필수 (책임 소재 기록)."""
    hourly_wage: float = Field(gt=0, le=1_000_000)
    reason: str = Field(min_length=5, max_length=300, description="수정 사유 (예: 2026-09 임금인상 반영, 계약서 갱신)")
    edited_by: str = Field(min_length=1, max_length=60, description="수정자 이름/직책")


class OvertimeIn(BaseModel):
    """연장·야간·휴일 가산수당 계산 입력. employee_id 를 주면 계약 시급·소정근로시간을 자동으로 쓴다."""
    employee_id: Optional[str] = None
    hourly_wage: Optional[float] = Field(default=None, gt=0, le=1_000_000)
    weekly_contract_hours: Optional[float] = Field(default=None, ge=0, le=168)
    overtime_hours: float = Field(default=0, ge=0, le=100)
    night_hours: float = Field(default=0, ge=0, le=100)
    holiday_hours: float = Field(default=0, ge=0, le=100)
    holiday_over_8h: float = Field(default=0, ge=0, le=100)
    employees_under_5: bool = False


class MinWageIn(BaseModel):
    employee_id: Optional[str] = None
    hourly_wage: Optional[float] = Field(default=None, gt=0, le=1_000_000)
    year: int = Field(default=2026, ge=2020, le=2035)


class WeeklyHolidayIn(BaseModel):
    employee_id: Optional[str] = None
    weekly_contract_hours: Optional[float] = Field(default=None, ge=0, le=168)
    daily_hours: float = Field(default=8, gt=0, le=24)
    hourly_wage: Optional[float] = Field(default=None, gt=0, le=1_000_000)


class FlexworkCheckIn(BaseModel):
    weekly_hours: list[float] = Field(min_length=1, max_length=6)
    core_hours_met: Optional[list[bool]] = None
    settlement_weeks: Optional[int] = Field(default=None, ge=1, le=6)
