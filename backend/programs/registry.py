"""programs/registry.py — 등록된 사업 목록. 프론트 탭·모드·빠른 질문·AI 도구가 전부 여기서 나온다.
새 사업 추가 = programs/<id>/knowledge.py(+rules.py) 만들고 아래 PROGRAMS 에 한 줄 추가. 다른 파일은 손대지 않는다.
각 knowledge 모듈은 ID, LABEL, LABEL_LONG, RULES(list[str]), MODES({mode: {title, steps}}), QUICK_QUESTIONS(list[(label, question)]) 를 가진다.
각 rules 모듈(선택)은 TOOLS = [(openai 함수 스키마, 구현 함수), ...] 를 가진다.
"""
from programs.common import knowledge as hr_knowledge, labor
from programs.flexwork import knowledge as flexwork_knowledge, rules as flexwork_rules
from programs.senior import knowledge as senior_knowledge, rules as senior_rules

PROGRAMS = {
    "senior": {"knowledge": senior_knowledge, "rules": senior_rules, "has_timeseries": True},
    "flexwork": {"knowledge": flexwork_knowledge, "rules": flexwork_rules, "has_timeseries": True},
    "hr": {"knowledge": hr_knowledge, "rules": labor, "has_timeseries": False},
}
TIMESERIES_PROGRAMS = [k for k, v in PROGRAMS.items() if v["has_timeseries"]]  # data 컬렉션의 program 값


def get(program_id: str) -> dict:
    if program_id not in PROGRAMS:
        raise KeyError(f"등록되지 않은 사업: {program_id}")
    return PROGRAMS[program_id]


def modes(program_id: str) -> dict:
    return get(program_id)["knowledge"].MODES


def list_programs() -> list[dict]:
    """GET /api/programs 응답 — 프론트 탭 구성용."""
    out = []
    for pid, p in PROGRAMS.items():
        k = p["knowledge"]
        out.append({
            "id": pid, "label": k.LABEL, "label_long": k.LABEL_LONG, "has_timeseries": p["has_timeseries"],
            "modes": [{"id": m, "title": v["title"]} for m, v in k.MODES.items()],
            "quick_questions": [{"label": a, "question": b} for a, b in k.QUICK_QUESTIONS],
            "tools": [s["function"]["name"] for s, _ in getattr(p["rules"], "TOOLS", [])],
        })
    return out


def tools_for(program_id: str, common_tools: list) -> tuple[list, dict]:
    """선택한 사업의 도구 + 공통 도구 → (OpenAI tools 스키마 목록, 이름→구현 함수)."""
    pairs = list(common_tools) + list(labor.TOOLS)
    p = get(program_id)
    if p["rules"] is not labor:
        pairs += getattr(p["rules"], "TOOLS", [])
    schemas = [s for s, _ in pairs]
    impl = {s["function"]["name"]: f for s, f in pairs}
    return schemas, impl
