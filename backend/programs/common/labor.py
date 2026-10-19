"""programs/common/labor.py — 근로기준법 공통 계산 (연장·야간·휴일 가산, 최저임금 비교, 주휴). 안내·계산만, 판정 없음.
모든 결과에 inputs·formula·basis·warnings·wage_source·disclaimer 를 붙여 "무엇을 근거로 어떻게 계산했는지"가 그대로 남게 한다.
시급은 우리가 산정하지 않는다 — 근로계약서 기재값(기업 입력) 또는 담당자 수정값을 그대로 쓰고 출처를 기록한다.
"""
CHECK_PHRASE = "지침 원문 확인 필요"

DISCLAIMER = (
    "입력값 기준 참고 계산이며 법적 효력이 없습니다. 통상임금 산정(고정수당 포함 여부 등)과 최종 판단·책임은 "
    "이용자에게 있으며, 분쟁 소지가 있으면 노무사·고용노동부 확인이 필요합니다."
)

# 출처: 최저임금위원회 고시. verified=False 면 결과 warnings 에 ⚠ 표시.
MIN_WAGE = {
    2025: {"value": 10_030, "verified": True, "source": "고용노동부 고시 제2024-xx호"},
    2026: {"value": 10_320, "verified": True, "source": "고용노동부 고시 (2026년 적용 최저임금)"},
}

WAGE_SOURCES = {
    "contract": "근로계약서 기재 시급(기업 입력값)",
    "edited": "담당자 수정값",
    "manual": "이용자 입력",
}


def _base(inputs: dict, wage_source: str) -> dict:
    return {
        "inputs": inputs,
        "wage_source": WAGE_SOURCES.get(wage_source, wage_source),
        "warnings": [],
        "disclaimer": DISCLAIMER,
    }


def _pos(name: str, v: float, allow_zero: bool = True) -> float:
    v = float(v)
    if v < 0 or (v == 0 and not allow_zero):
        raise ValueError(f"{name} 은(는) {'0 이상' if allow_zero else '0보다 큰 값'}이어야 합니다")
    return v


def calc_overtime(hourly_wage: float, weekly_contract_hours: float, overtime_hours: float = 0,
                  night_hours: float = 0, holiday_hours: float = 0, holiday_over_8h: float = 0,
                  employees_under_5: bool = False, wage_source: str = "manual") -> dict:
    """연장·야간·휴일 가산수당 (근로기준법 제56조).
    - 연장: 통상시급 × 1.5 × 연장시간
    - 야간(22~06시): 통상시급 × 0.5 × 야간시간 (기본급은 연장/소정 쪽에 이미 포함된 것으로 보고 가산분만)
    - 휴일: 8시간 이내 1.5배, 8시간 초과분 2.0배
    5인 미만 사업장은 제56조 가산이 적용되지 않을 수 있어(제11조·시행령) 두 경우 금액을 모두 보여주고 ⚠ 만 단다.
    """
    w = _pos("hourly_wage", hourly_wage, allow_zero=False)
    c = _pos("weekly_contract_hours", weekly_contract_hours)
    ot, nt, hd, hd8 = (_pos("overtime_hours", overtime_hours), _pos("night_hours", night_hours),
                       _pos("holiday_hours", holiday_hours), _pos("holiday_over_8h", holiday_over_8h))
    if hd8 > hd:
        raise ValueError("holiday_over_8h 는 holiday_hours 이하여야 합니다")
    r = _base({"hourly_wage": w, "weekly_contract_hours": c, "overtime_hours": ot, "night_hours": nt,
               "holiday_hours": hd, "holiday_over_8h": hd8, "employees_under_5": employees_under_5}, wage_source)

    overtime_pay = round(w * 1.5 * ot)
    night_extra = round(w * 0.5 * nt)
    holiday_pay = round(w * 1.5 * (hd - hd8) + w * 2.0 * hd8)
    total_with = overtime_pay + night_extra + holiday_pay
    # 가산 미적용(5인 미만 가능성): 연장·휴일 근로는 시급 1.0배, 야간 가산 없음
    total_without = round(w * 1.0 * ot + w * 1.0 * hd)

    r.update({
        "overtime_pay": overtime_pay, "night_extra": night_extra, "holiday_pay": holiday_pay,
        "total": total_with,
        "total_if_no_premium": total_without,
        "formula": (f"연장 {w:,.0f}×1.5×{ot:g} = {overtime_pay:,} / 야간가산 {w:,.0f}×0.5×{nt:g} = {night_extra:,} / "
                    f"휴일 {w:,.0f}×1.5×{hd - hd8:g} + {w:,.0f}×2.0×{hd8:g} = {holiday_pay:,} → 합계 {total_with:,}원"),
        "basis": ["근로기준법 제56조(연장·야간 및 휴일 근로) — 연장·야간 50% 이상, 휴일 8시간 이내 50%·초과 100% 가산",
                  "근로기준법 제50조(근로시간) — 1주 40시간·1일 8시간", "근로기준법 제53조(연장 근로의 제한) — 1주 12시간 한도"],
    })
    if c > 40:
        r["warnings"].append(f"⚠ 주 소정근로시간 {c:g}h 가 법정 40h 를 넘습니다 — 계약 내용 확인 필요")
    if ot > 12:
        r["warnings"].append(f"⚠ 연장 {ot:g}h 가 주 12h 한도(제53조)를 넘습니다 — 주 단위 입력인지 확인")
    if employees_under_5:
        r["warnings"].append(f"⚠ 5인 미만 사업장은 제56조 가산이 적용되지 않을 수 있습니다 (적용 시 {total_with:,}원 / "
                             f"미적용 시 {total_without:,}원) — 상시근로자 수 산정과 적용 여부는 노무사·고용노동부 확인")
    if nt and not ot and not hd:
        r["warnings"].append("ℹ 야간 가산(0.5배)만 계산했습니다. 해당 시간의 기본급(1.0배)은 소정·연장 쪽에 포함돼 있는지 확인")
    return r


def check_min_wage(hourly_wage: float, year: int = 2026, wage_source: str = "manual") -> dict:
    """최저임금 비교 — 미달이면 ⚠ 경고만 (판정 아님)."""
    w = _pos("hourly_wage", hourly_wage, allow_zero=False)
    if year not in MIN_WAGE:
        raise ValueError(f"{year}년 최저임금 값이 등록돼 있지 않습니다 ({', '.join(map(str, MIN_WAGE))})")
    m = MIN_WAGE[year]
    r = _base({"hourly_wage": w, "year": year}, wage_source)
    diff = round(w - m["value"])
    r.update({
        "min_wage": m["value"], "difference": diff, "meets": diff >= 0,
        "monthly_209h": m["value"] * 209,
        "formula": f"{w:,.0f} − {m['value']:,} = {diff:+,}원/시간 (월 환산 209h 기준 최저 {m['value'] * 209:,}원)",
        "basis": [f"최저임금법 제6조 — {year}년 시간급 {m['value']:,}원 ({m['source']})",
                  "월 환산 209시간 = (주 40h + 주휴 8h) × 365/7 ÷ 12"],
    })
    if not m["verified"]:
        r["warnings"].append(f"⚠ {year}년 최저임금 값 미확인 — {CHECK_PHRASE}")
    if diff < 0:
        r["warnings"].append(f"⚠ 입력 시급이 {year}년 최저임금보다 {-diff:,}원 낮습니다 — 계약서·통상임금 산정 확인 필요 (판정 아님)")
    return r


def calc_weekly_holiday(weekly_contract_hours: float, daily_hours: float = 8, hourly_wage: float | None = None,
                        wage_source: str = "manual") -> dict:
    """주휴 발생 여부·시간 (근로기준법 제55조, 시행령 제30조). 주 15시간 이상이면 발생."""
    c = _pos("weekly_contract_hours", weekly_contract_hours)
    d = _pos("daily_hours", daily_hours, allow_zero=False)
    r = _base({"weekly_contract_hours": c, "daily_hours": d, "hourly_wage": hourly_wage}, wage_source)
    eligible = c >= 15
    hours = round(min(c, 40) / 40 * 8, 2) if eligible else 0
    pay = round(hourly_wage * hours) if (hourly_wage and eligible) else None
    r.update({
        "eligible": eligible, "weekly_holiday_hours": hours, "weekly_holiday_pay": pay,
        "formula": f"주휴시간 = min({c:g}, 40) ÷ 40 × 8 = {hours}h" + (f" × {hourly_wage:,.0f} = {pay:,}원" if pay else ""),
        "basis": ["근로기준법 제55조(휴일) — 1주 소정근로일 개근 시 유급휴일 1일",
                  "근로기준법 제18조 제3항 — 4주 평균 1주 15시간 미만은 제55조 미적용"],
    })
    if not eligible:
        r["warnings"].append("ℹ 주 15시간 미만은 주휴 미발생 (제18조 제3항) — 4주 평균 기준인지 확인")
    r["warnings"].append("⚠ 주휴는 소정근로일 개근이 전제 — 결근 주의 처리와 단시간 근로자 산정 방식은 노무사 확인")
    return r


TOOLS = [
    ({"type": "function", "function": {
        "name": "calc_overtime",
        "description": "연장·야간·휴일 가산수당 계산 (근로기준법 제56조). 시급은 get_contract_wage 결과의 hourly_wage 와 wage_source 를 그대로 넘긴다.",
        "parameters": {"type": "object", "properties": {
            "hourly_wage": {"type": "number"}, "weekly_contract_hours": {"type": "number"},
            "overtime_hours": {"type": "number"}, "night_hours": {"type": "number"},
            "holiday_hours": {"type": "number"}, "holiday_over_8h": {"type": "number"},
            "employees_under_5": {"type": "boolean"},
            "wage_source": {"type": "string", "enum": ["contract", "edited", "manual"]}},
            "required": ["hourly_wage", "weekly_contract_hours"]}}}, calc_overtime),
    ({"type": "function", "function": {
        "name": "check_min_wage",
        "description": "시급을 해당 연도 최저임금과 비교 (경고만, 판정 아님).",
        "parameters": {"type": "object", "properties": {
            "hourly_wage": {"type": "number"}, "year": {"type": "integer"},
            "wage_source": {"type": "string", "enum": ["contract", "edited", "manual"]}},
            "required": ["hourly_wage"]}}}, check_min_wage),
    ({"type": "function", "function": {
        "name": "calc_weekly_holiday",
        "description": "주 소정근로시간으로 주휴 발생 여부·주휴시간·주휴수당 계산 (근로기준법 제55조).",
        "parameters": {"type": "object", "properties": {
            "weekly_contract_hours": {"type": "number"}, "daily_hours": {"type": "number"},
            "hourly_wage": {"type": "number"},
            "wage_source": {"type": "string", "enum": ["contract", "edited", "manual"]}},
            "required": ["weekly_contract_hours"]}}}, calc_weekly_holiday),
]
