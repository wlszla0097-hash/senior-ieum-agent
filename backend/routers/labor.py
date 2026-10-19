"""routers/labor.py — 근로기준법 계산 창구 (프론트 'HR 공통 계산' 탭용). 계산은 programs/common/labor.py·programs/flexwork/rules.py 가 한다.
employee_id 를 주면 계약 시급·소정근로시간을 contracts 에서 가져와 쓰고, 결과에 출처(계약서값/담당자 수정값·이력)를 붙인다.
"""
from fastapi import APIRouter, HTTPException
from models import FlexworkCheckIn, MinWageIn, OvertimeIn, WeeklyHolidayIn
from programs.common import labor
from programs.flexwork import rules as flexwork_rules
from services import contracts

router = APIRouter(prefix="/api/labor", tags=["labor"])


def _resolve(employee_id: str | None, hourly_wage: float | None, weekly_hours: float | None = None):
    """(시급, 주 소정근로시간, wage_source, 직원 정보). 직원이 있으면 계약서 값, 없으면 이용자 입력."""
    if employee_id:
        e = contracts.get_employee(employee_id)
        if not e:
            raise HTTPException(404, "직원을 찾을 수 없습니다")
        return (hourly_wage or e["hourly_wage"], weekly_hours or e["weekly_contract_hours"],
                "manual" if hourly_wage and hourly_wage != e["hourly_wage"] else e["wage_source"], e)
    if hourly_wage is None:
        raise HTTPException(422, "employee_id 또는 hourly_wage 중 하나는 필요합니다")
    return hourly_wage, weekly_hours, "manual", None


def _attach(result: dict, e: dict | None) -> dict:
    if e:
        result["employee"] = {k: e[k] for k in ("employee_id", "name", "site", "contract_hourly_wage", "wage_history")}
    return result


@router.post("/overtime")
def overtime(body: OvertimeIn):
    """연장·야간·휴일 가산수당 (근로기준법 제56조). 결과에 계산식·조문·출처·⚠·고지 포함."""
    w, c, src, e = _resolve(body.employee_id, body.hourly_wage, body.weekly_contract_hours)
    if c is None:
        raise HTTPException(422, "weekly_contract_hours 가 필요합니다")
    try:
        r = labor.calc_overtime(w, c, body.overtime_hours, body.night_hours, body.holiday_hours,
                                body.holiday_over_8h, body.employees_under_5, src)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err
    return _attach(r, e)


@router.post("/min-wage")
def min_wage(body: MinWageIn):
    w, _, src, e = _resolve(body.employee_id, body.hourly_wage)
    try:
        return _attach(labor.check_min_wage(w, body.year, src), e)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err


@router.post("/weekly-holiday")
def weekly_holiday(body: WeeklyHolidayIn):
    if body.employee_id:
        w, c, src, e = _resolve(body.employee_id, body.hourly_wage, body.weekly_contract_hours)
        daily = body.daily_hours if body.daily_hours != 8 else (e.get("daily_hours") or 8)
    else:
        if body.weekly_contract_hours is None:
            raise HTTPException(422, "employee_id 또는 weekly_contract_hours 가 필요합니다")
        w, c, src, e, daily = body.hourly_wage, body.weekly_contract_hours, "manual", None, body.daily_hours
    try:
        return _attach(labor.calc_weekly_holiday(c, daily, w, src), e)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err


@router.post("/flexwork-check")
def flexwork_check(body: FlexworkCheckIn):
    """선택근무제 정산기간 점검 — 항목별 충족/미충족 목록 (판정 아님)."""
    try:
        return flexwork_rules.check_flexwork(body.weekly_hours, body.core_hours_met, body.settlement_weeks)
    except ValueError as err:
        raise HTTPException(422, str(err)) from err
