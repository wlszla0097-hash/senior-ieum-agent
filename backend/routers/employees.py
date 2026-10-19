"""routers/employees.py — 직원(가명) 계약 시급 조회·담당자 수정 창구. 원값은 지우지 않고 수정 이력을 누적한다."""
from fastapi import APIRouter, HTTPException
from models import WageUpdate
from services import contracts

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.get("")
def list_employees():
    """직원 목록 (계약 시급·출처 포함). 비어 있으면 POST /api/data/seed 로 합성 직원 5명을 넣는다."""
    return contracts.list_employees()


@router.get("/{employee_id}")
def get_employee(employee_id: str):
    e = contracts.get_employee(employee_id)
    if not e:
        raise HTTPException(404, "직원을 찾을 수 없습니다")
    return e


@router.put("/{employee_id}/wage")
def update_wage(employee_id: str, body: WageUpdate):
    """담당자 수정: 시급·사유(5자 이상)·수정자 필수. 이후 계산은 수정값을 쓰고 wage_source='담당자 수정값' 으로 기록된다."""
    e = contracts.update_wage(employee_id, body.hourly_wage, body.reason.strip(), body.edited_by.strip())
    if not e:
        raise HTTPException(404, "직원을 찾을 수 없습니다")
    return e
