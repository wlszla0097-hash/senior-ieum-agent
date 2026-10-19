"""programs/flexwork/rules.py — 선택근무제 규칙엔진: 정산기간 주별 근로시간으로 요건 충족 항목을 코드로 점검 (판정 아님, 항목별 충족/미충족 목록).
입력 형식은 AI-data_analysis 저장소의 주별 집계(주차 순서대로 시간 목록)와 맞춘다.
"""
from statistics import mean

from programs.common.labor import CHECK_PHRASE, DISCLAIMER
from programs.flexwork.knowledge import PARAMS


def check_flexwork(weekly_hours: list[float], core_hours_met: list[bool] | None = None,
                   settlement_weeks: int | None = None) -> dict:
    """정산기간 평균 주 근로시간 ≤ 40h, 의무근로시간대 충족, 미달·초과 주 목록."""
    if not weekly_hours:
        raise ValueError("weekly_hours 는 1주 이상이어야 합니다")
    hours = [float(h) for h in weekly_hours]
    if any(h < 0 or h > 168 for h in hours):
        raise ValueError("주 근로시간은 0~168 범위여야 합니다")
    weeks = settlement_weeks or len(hours)
    core = list(core_hours_met) if core_hours_met is not None else None
    if core is not None and len(core) != len(hours):
        raise ValueError("core_hours_met 길이는 weekly_hours 와 같아야 합니다")

    legal = PARAMS["legal_weekly_hours"]["value"]
    avg = round(mean(hours), 2)
    over = [i + 1 for i, h in enumerate(hours) if h > legal]
    under = [i + 1 for i, h in enumerate(hours) if h < legal]
    core_miss = [] if core is None else [i + 1 for i, ok in enumerate(core) if not ok]

    items = [
        {"item": f"정산기간 평균 주 근로시간 ≤ {legal}h", "met": avg <= legal, "detail": f"평균 {avg}h ({len(hours)}주)"},
        {"item": f"정산기간 {PARAMS['settlement_max_weeks']['value']}주(1개월) 이내", "met": weeks <= PARAMS["settlement_max_weeks"]["value"],
         "detail": f"{weeks}주"},
        {"item": "의무근로시간대 전 주 충족", "met": core is not None and not core_miss,
         "detail": "입력 없음" if core is None else (f"미충족 주: {core_miss}" if core_miss else "전 주 충족")},
    ]
    warnings = [f"⚠ {PARAMS[k]['label']}" for k in ("settlement_max_weeks", "core_hours_required") if not PARAMS[k]["verified"]]
    if over:
        warnings.append(f"ℹ {legal}h 초과 주 {over} — 정산기간 평균이 40h 이내면 연장 아님(제52조), 초과분은 평균으로 흡수되는지 확인")
    if under:
        warnings.append(f"ℹ {legal}h 미달 주 {under} — 소정근로시간 미달이면 지원 요건·급여 산정에 영향 가능, 전자출결 누락인지 먼저 확인")
    warnings.append("ℹ 2026 지급 요건은 근로자별 월 6시간 이상 단축(단축일 1시간 이상)·월 30만원 — 이 점검은 정산기간 근로시간만 본다")
    return {
        "program": "flexwork",
        "inputs": {"weekly_hours": hours, "core_hours_met": core, "settlement_weeks": weeks},
        "average_weekly_hours": avg,
        "items": items,
        "all_met": all(i["met"] for i in items),
        "formula": f"평균 = ({' + '.join(f'{h:g}' for h in hours)}) ÷ {len(hours)} = {avg}h",
        "basis": ["근로기준법 제52조(선택적 근로시간제) — 1개월 이내 정산기간 평균 1주 40h 이내, 근로자대표 서면합의",
                  "고용노동부 일생활균형 지원금 2026 운영 기준 — 월 6시간 이상 단축, 월 30만원·연 360만원"],
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
    }


TOOLS = [
    ({"type": "function", "function": {
        "name": "check_flexwork",
        "description": "선택근무제 정산기간 점검: 주별 근로시간 목록(과 의무근로시간대 충족 여부)로 평균 ≤ 40h·정산기간·의무시간대 항목별 충족 여부를 계산.",
        "parameters": {"type": "object", "properties": {
            "weekly_hours": {"type": "array", "items": {"type": "number"}, "description": "주차 순서대로 주 근로시간"},
            "core_hours_met": {"type": "array", "items": {"type": "boolean"}},
            "settlement_weeks": {"type": "integer"}},
            "required": ["weekly_hours"]}}}, check_flexwork),
]
