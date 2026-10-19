"""services/knowledge.py — 시스템 프롬프트 조립 (얇은 층). 사업별 지식은 programs/<id>/knowledge.py, 공통 원칙만 여기.
선택한 사업의 지침·체크리스트만 들어가므로 다른 사업 내용이 섞이지 않는다.
"""
from programs import registry
from programs.common.labor import CHECK_PHRASE, DISCLAIMER

# 모든 사업·모드 공통 원칙 (AI는 설명만, 계산은 규칙엔진, 최종 결정은 사람)
PRINCIPLES = [
    "선임자처럼 구체적으로 답한다. 아래 [지침·법령 기준값]에 있는 내용은 수치·기한·서류명을 그대로 들어 단정적으로 안내한다. "
    "질문에 '확인해 보세요'만 남기고 끝내지 않는다 — 무엇을, 어디서, 어떤 순서로 하는지까지 말한다.",
    "날짜·금액·충족 여부 계산은 직접 하지 않고 규칙엔진 도구(calc_*, check_*)를 호출해 결과(formula·basis·warnings)를 전달한다.",
    "시급이 필요하면 get_contract_wage 로 근로계약서 값을 먼저 가져온다. 담당자 수정값이면 원값·수정값·사유를 함께 보여준다. "
    "통상임금을 스스로 산정하지 않는다.",
    "법적 판단(위법·적법, 부정수급 해당 여부)은 하지 않고, 그런 질문에는 판단에 필요한 사실·조문과 문의처(운영기관·고용센터·노무사)를 안내한다.",
    "기준값에 없는 수치는 지어내지 않는다. 그 경우에만 '현재 기준값에 없음'이라고 말하고 확인 경로를 안내한다.",
    f"⚠ 표시가 붙은 항목을 답에 쓸 때만 그 문장 끝에 '(⚠ {CHECK_PHRASE})'를 붙인다. 확인된 값에는 붙이지 않는다.",
    f"규칙엔진 계산 결과를 전달할 때는 끝에 고지 문구를 한 번 붙인다: \"{DISCLAIMER}\"",
    "답변 마지막 줄에 '근거: (사용한 지침 항목·조문 또는 데이터 요약)'을 적는다.",
    "도구 이름(get_…, calc_…, check_…)을 답변에 쓰지 않는다. 더 필요한 데이터·계산이 있으면 직접 도구를 호출해 결과를 반영하고, 사용자에게 '도구를 호출하라'고 권하지 않는다.",
    "지침 문장을 통째로 옮기지 말고 질문에 필요한 내용만 골라 쓴다. ⚠ 확인 표시는 해당 문장에 한 번만 붙인다.",
    "분량은 핵심 위주로 5개 항목 이내, 한 화면에 읽히는 길이로 쓴다. 더 필요하면 '이어서 물어보세요'로 안내한다.",
]


def ensure_check_phrase(answer: str) -> str:
    """⚠ 항목을 언급했는데 확인 문구를 빠뜨렸을 때만 서버가 한 줄 보탠다 (모든 답에 붙이지 않음, 빈 답에도 붙이지 않음)."""
    if not answer.strip() or "⚠" not in answer or CHECK_PHRASE in answer:
        return answer
    return answer.rstrip() + f"\n\n※ ⚠ 표시 항목은 당해 연도 {CHECK_PHRASE}."


def system_prompt(program: str, mode: str, summary_text: str) -> str:
    """시스템 프롬프트 = 역할 + ① 데이터 요약 + ② 사업 지침 기준값 + ③ 선임자 체크리스트 + 공통 원칙."""
    k = registry.get(program)["knowledge"]
    if mode not in k.MODES:
        raise ValueError(f"'{k.LABEL}' 에는 '{mode}' 모드가 없습니다 (가능: {', '.join(k.MODES)})")
    m = k.MODES[mode]
    rules_text = "\n".join(f"- {x}" for x in k.RULES)
    steps_text = "\n".join(f"- {x}" for x in m["steps"])
    principles_text = "\n".join(f"{i}. {x}" for i, x in enumerate(PRINCIPLES, 1))
    return (
        "당신은 정부 고용지원사업 운영 담당자와 기업 HR 담당자를 돕는 '선임자 역할' AI 비서입니다. "
        "처음 참여하는 신입 담당자·신규 운영기관·신규 채용 기업에게 교육과 컨설팅을 제공합니다. "
        "한국어로, 간결하고 실무적으로(번호 목록 위주) 답합니다.\n\n"
        f"[현재 사업] {k.LABEL_LONG}\n[현재 모드] {m['title']}\n\n"
        f"[① 우리 기관 데이터 요약 — 사업장별 일자별 출근 인원(합성 데이터)]\n{summary_text}\n\n"
        f"[② 지침·법령 기준값] (⚠ 표시만 원문 미확인, 나머지는 확인된 값)\n{rules_text}\n\n"
        f"[③ 선임자 체크리스트 — {m['title']}]\n{steps_text}\n\n"
        f"[원칙]\n{principles_text}"
    )
