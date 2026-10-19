"""services/contracts.py — 근로계약서 기재값(계약 시급·소정근로시간) 조회 + 담당자 수정 이력. 추후 이음24 읽기 전용 API 로 교체할 자리.
과제 단계: Firestore 컬렉션 employees 의 합성 데이터(가명·(가상))만. 시급은 우리가 산정하지 않고 '기업이 계약서에 쓴 값'을 그대로 돌려주며,
담당자가 수정하면 원값을 지우지 않고 wage_history 에 {before, after, reason, edited_by, edited_at} 를 누적한다.
"""
from datetime import datetime, timezone

from services import db

COLLECTION = "employees"

SEED = [  # 전부 가명·(가상). 계약 시급은 근로계약서에 기재된 값이라는 전제
    {"employee_id": "E001", "name": "김가명", "site": "(가상)A사", "program": "senior", "hourly_wage": 10_500, "weekly_contract_hours": 30, "daily_hours": 6, "contract_date": "2026-06-01"},
    {"employee_id": "E002", "name": "이가명", "site": "(가상)A사", "program": "senior", "hourly_wage": 10_320, "weekly_contract_hours": 25, "daily_hours": 5, "contract_date": "2026-06-01"},
    {"employee_id": "E003", "name": "박가명", "site": "(가상)B사", "program": "senior", "hourly_wage": 10_000, "weekly_contract_hours": 20, "daily_hours": 4, "contract_date": "2026-07-01"},
    {"employee_id": "E004", "name": "최가명", "site": "(가상)C사", "program": "flexwork", "hourly_wage": 14_000, "weekly_contract_hours": 40, "daily_hours": 8, "contract_date": "2026-03-02"},
    {"employee_id": "E005", "name": "정가명", "site": "(가상)D사", "program": "flexwork", "hourly_wage": 12_500, "weekly_contract_hours": 40, "daily_hours": 8, "contract_date": "2026-04-01"},
]


def seed() -> int:
    if db.count(COLLECTION) > 0:
        return 0
    return db.bulk_create(COLLECTION, [{**e, "wage_history": []} for e in SEED])


def list_employees() -> list[dict]:
    rows = db.list_all(COLLECTION)
    rows.sort(key=lambda r: r.get("employee_id", ""))
    return [_view(r) for r in rows]


def _find(employee_id: str) -> dict | None:
    for r in db.list_all(COLLECTION):
        if r.get("employee_id") == employee_id or r.get("id") == employee_id:
            return r
    return None


def _view(r: dict) -> dict:
    """응답 형태: 현재 시급과 출처, 수정 이력. 계산 도구는 hourly_wage·wage_source 를 그대로 넘긴다."""
    hist = r.get("wage_history") or []
    return {
        "id": r["id"], "employee_id": r.get("employee_id"), "name": r.get("name"), "site": r.get("site"),
        "program": r.get("program"), "contract_date": r.get("contract_date"),
        "hourly_wage": r.get("hourly_wage"), "weekly_contract_hours": r.get("weekly_contract_hours"),
        "daily_hours": r.get("daily_hours"),
        "wage_source": "edited" if hist else "contract",
        "wage_source_label": "담당자 수정값" if hist else "근로계약서 기재 시급(기업 입력값)",
        "contract_hourly_wage": hist[0]["before"] if hist else r.get("hourly_wage"),
        "wage_history": hist,
    }


def get_employee(employee_id: str) -> dict | None:
    r = _find(employee_id)
    return _view(r) if r else None


def update_wage(employee_id: str, hourly_wage: float, reason: str, edited_by: str) -> dict | None:
    r = _find(employee_id)
    if not r:
        return None
    entry = {"before": r.get("hourly_wage"), "after": hourly_wage, "reason": reason, "edited_by": edited_by,
             "edited_at": datetime.now(timezone.utc).isoformat()}
    hist = (r.get("wage_history") or []) + [entry]
    updated = db.update(COLLECTION, r["id"], {"hourly_wage": hourly_wage, "wage_history": hist})
    return _view(updated) if updated else None


# ---------- GPT 도구 ----------

def tool_get_contract_wage(employee_id: str) -> dict:
    e = get_employee(employee_id)
    if not e:
        return {"error": f"직원 {employee_id} 을 찾을 수 없습니다. 목록은 list_employees 로 확인"}
    return {k: e[k] for k in ("employee_id", "name", "site", "program", "hourly_wage", "weekly_contract_hours",
                               "daily_hours", "wage_source", "wage_source_label", "contract_hourly_wage", "wage_history")}


def tool_list_employees() -> list[dict]:
    return [{k: e[k] for k in ("employee_id", "name", "site", "program", "hourly_wage", "wage_source_label")} for e in list_employees()]


TOOLS = [
    ({"type": "function", "function": {
        "name": "get_contract_wage",
        "description": "직원의 근로계약서 기재 시급·주 소정근로시간과 출처(계약서값/담당자 수정값, 수정 이력)를 조회. 금액 계산 전 반드시 호출.",
        "parameters": {"type": "object", "properties": {"employee_id": {"type": "string", "description": "예: E001"}},
                       "required": ["employee_id"]}}}, tool_get_contract_wage),
    ({"type": "function", "function": {
        "name": "list_employees",
        "description": "등록된 직원(가명) 목록과 계약 시급 조회.",
        "parameters": {"type": "object", "properties": {}, "required": []}}}, tool_list_employees),
]
