"""programs/senior/rules.py — 시니어인턴십 규칙엔진: 지원 회차·신청 기한·예상 지원액을 AI 대신 코드로 계산 (GPT는 설명만).
수치는 같은 폴더 knowledge.PARAMS 에서 가져오고, 미확인(⚠) 값을 썼으면 결과 warnings 에 표시한다.
"""
import calendar
from datetime import date, timedelta

from programs.common.labor import CHECK_PHRASE
from programs.senior.knowledge import PARAMS as SENIOR_PARAMS


def _add_months(d: date, months: int) -> date:
    """d 에서 months 개월 뒤 같은 날 (말일 보정: 1/31 + 1개월 = 2/28)."""
    y, m = divmod(d.month - 1 + months, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _d_day(target: date, today: date) -> str:
    n = (target - today).days
    return f"D-{n}" if n > 0 else "D-DAY" if n == 0 else f"D+{-n} (기한 경과)"


def _parse(s: str) -> date:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError as e:
        raise ValueError(f"날짜 형식은 YYYY-MM-DD 여야 합니다: {s}") from e


def _warnings(keys: list[str]) -> list[str]:
    return [f"⚠ {SENIOR_PARAMS[k]['label']} = {SENIOR_PARAMS[k]['value']} — {CHECK_PHRASE}"
            for k in keys if not SENIOR_PARAMS[k]["verified"]]


def calc_senior_schedule(start_date: str, monthly_wage: int = 2_000_000, hire_type: str = "intern",
                         today: str | None = None) -> dict:
    """시니어인턴십 회차별 지원기준일·신청 가능일·마감일·예상 지원액.
    회차 n 의 지원기준일 = 근로(또는 계속고용) 시작일 + n개월 - 1일 (n개월 근무를 채운 날).
    """
    if monthly_wage <= 0:
        raise ValueError("monthly_wage 는 0보다 커야 합니다")
    if hire_type not in ("intern", "hire"):
        raise ValueError("hire_type 은 intern(인턴) 또는 hire(계속고용) 입니다")
    start = _parse(start_date)
    now = _parse(today) if today else date.today()
    p = {k: v["value"] for k, v in SENIOR_PARAMS.items()}
    prefix = "intern" if hire_type == "intern" else "hire"
    months, rate, cap = p[f"{prefix}_months"], p[f"{prefix}_rate"], p[f"{prefix}_cap"]
    monthly_support = int(min(monthly_wage * rate, cap))

    rounds = []
    for n in range(1, months + 1):
        base = _add_months(start, n) - timedelta(days=1)
        deadline = base + timedelta(days=p["apply_days"])
        rounds.append({
            "round": n,
            "basis_date": str(base),           # 지원기준일
            "apply_from": str(base + timedelta(days=1)),
            "deadline": str(deadline),
            "d_day": _d_day(deadline, now),
            "expected_amount": monthly_support,
        })
    return {
        "program": "senior",
        "hire_type": hire_type,
        "start_date": str(start),
        "monthly_wage": monthly_wage,
        "rounds": rounds,
        "total_expected": monthly_support * months,
        "warnings": _warnings([f"{prefix}_months", f"{prefix}_rate", f"{prefix}_cap", "apply_days"]),
        "note": "규칙엔진 계산값입니다. 실제 지급액·기한은 운영기관 승인 내용과 당해 연도 지침이 우선합니다.",
    }


def calc_deadline(base_date: str, days: int, today: str | None = None) -> dict:
    """기준일 + days 일 = 기한, 오늘 기준 D-day. (선택근무제 정산기간·신청 기한 등 어떤 사업에도 사용)"""
    if not -366 <= days <= 366:
        raise ValueError("days 는 -366~366 범위여야 합니다")
    base = _parse(base_date)
    now = _parse(today) if today else date.today()
    deadline = base + timedelta(days=days)
    return {"base_date": str(base), "days": days, "deadline": str(deadline),
            "weekday": "월화수목금토일"[deadline.weekday()], "d_day": _d_day(deadline, now),
            "note": "주말·공휴일 연장 여부는 지침에서 확인하세요. 일수 자체가 지침 기준인지도 확인 필요."}


# ---------- GPT 도구 등록 (registry 가 모아서 ai.py 에 넘긴다) ----------

def tool_calc_senior_schedule(start_date: str, monthly_wage: int = 2_000_000, hire_type: str = "intern") -> dict:
    """SENIOR_API_URL(외부 Senior_ieum 규칙엔진)이 있으면 그쪽을 먼저, 없거나 실패하면 내장 엔진."""
    import json
    import os
    import urllib.parse
    import urllib.request
    base = os.getenv("SENIOR_API_URL")
    if base:
        q = urllib.parse.urlencode({"op": "schedule", "start": start_date, "wage": monthly_wage, "type": hire_type})
        try:
            with urllib.request.urlopen(f"{base.rstrip('/')}/api/senior?{q}", timeout=8) as r:
                return {"engine": "external", **json.loads(r.read().decode())}
        except Exception:  # noqa: BLE001 — 외부 실패 시 내장 엔진으로 대체
            pass
    return {"engine": "builtin", **calc_senior_schedule(start_date, monthly_wage, hire_type)}


TOOLS = [
    ({"type": "function", "function": {
        "name": "calc_senior_schedule",
        "description": "시니어인턴십 근로(계속고용) 시작일·월급으로 회차별 지원기준일·신청 가능일·마감일·D-day·예상 지원액을 규칙엔진이 계산.",
        "parameters": {"type": "object", "properties": {
            "start_date": {"type": "string", "description": "YYYY-MM-DD"},
            "monthly_wage": {"type": "integer", "description": "월 급여(원)"},
            "hire_type": {"type": "string", "enum": ["intern", "hire"], "description": "intern=인턴 기간, hire=계속고용"}},
            "required": ["start_date"]}}}, tool_calc_senior_schedule),
]
