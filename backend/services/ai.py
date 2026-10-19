"""services/ai.py — OpenAI 호출: 시스템 프롬프트 주입 + 도구 호출(Function Calling) 루프 + 비용 통제. 도구는 사업별로 registry 가 모아 준다.
비용 통제: 모델 AI_MODEL(기본 gpt-4o-mini), max_tokens 700 (gpt-5 등 추론 모델은 max_completion_tokens 4000·reasoning_effort low, temperature 생략), 최근 10개 메시지만 전송, 도구 호출 최대 2라운드.
키가 없으면 호출하지 않고 안내 문구를 돌려준다 (나머지 기능은 전부 동작).
"""
import json
import os
import time

from programs import registry
from programs.senior import rules as senior_rules
from services import contracts, db, knowledge, summary as summary_svc

MAX_TOKENS = 700
HISTORY_LIMIT = 10   # 최근 10개 메시지만 보내 토큰 절약
MAX_TOOL_ROUNDS = 2  # 도구 호출 최대 2라운드
NO_KEY_ANSWER = ("[AI 미설정] OPENAI_API_KEY 가 없어 AI 답변을 만들지 못했습니다. "
                 "데이터 관리·요약·대화 저장은 정상 동작합니다. 키를 넣으면 이 자리에 답변이 옵니다.")


class AIError(Exception):
    """OpenAI 호출 실패(키 오류·한도 초과·시간 초과 등). 라우터가 502 로 바꿔 돌려준다."""


def is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def model_name() -> str:
    return os.getenv("AI_MODEL", "gpt-4o-mini")


REASONING_MAX_TOKENS = 4000  # 추론 모델은 '생각'에도 토큰을 쓴다. 한도가 작으면 생각만 하다 본문이 비어 버린다
REASONING_EFFORT = os.getenv("AI_REASONING_EFFORT", "low").strip()  # minimal|low|medium|high, 비우면 안 보냄
_EFFORT_UNSUPPORTED = False  # 게이트웨이가 reasoning_effort 를 거절한 적이 있으면 True (교육장 게이트웨이는 미지원)


def is_reasoning_model(model: str) -> bool:
    """gpt-5·o1·o3·o4 계열 = 추론 모델: max_tokens 대신 max_completion_tokens, temperature 는 기본값(1)만 허용."""
    m = model.lower().split("/")[-1]
    return m.startswith(("gpt-5", "o1", "o3", "o4"))


def gen_params(model: str) -> dict:
    """모델 종류에 맞는 생성 옵션 (교육장 게이트웨이 gpt-5-mini 와 gpt-4o-mini 둘 다 동작하게)."""
    if is_reasoning_model(model):
        p = {"max_completion_tokens": REASONING_MAX_TOKENS}
        if REASONING_EFFORT:
            p["reasoning_effort"] = REASONING_EFFORT
        return p
    return {"max_tokens": MAX_TOKENS, "temperature": 0.3}


# ---------- 도구: 데이터 도구(여기) + 계약 도구(contracts) + 사업별 규칙엔진(programs/registry) ----------

def tool_get_data_summary(program: str | None = None) -> dict:
    return summary_svc.build(db.list_all("data"), program or None)


def tool_get_recent_records(program: str = "senior", site: str | None = None, n: int = 10) -> list:
    n = max(1, min(int(n), 30))
    rows = [r for r in db.list_all("data") if r.get("program") == program and (not site or r.get("site") == site)]
    rows.sort(key=lambda r: str(r.get("date")))
    return [{"date": str(r["date"]), "value": r["value"], "site": r.get("site"), "memo": r.get("memo", "")} for r in rows[-n:]]


def tool_calc_deadline(base_date: str, days: int) -> dict:
    return senior_rules.calc_deadline(base_date, days)


COMMON_TOOLS = [
    ({"type": "function", "function": {
        "name": "get_data_summary",
        "description": "저장된 출근 기록 시계열의 요약(기간·건수·평균/최대/최소·최근 30일 추세). program 생략 시 두 사업 비교.",
        "parameters": {"type": "object", "properties": {
            "program": {"type": "string", "enum": registry.TIMESERIES_PROGRAMS}}, "required": []}}}, tool_get_data_summary),
    ({"type": "function", "function": {
        "name": "get_recent_records",
        "description": "특정 사업(·사업장)의 최근 출근 기록 n건(메모 포함)을 날짜순으로 조회.",
        "parameters": {"type": "object", "properties": {
            "program": {"type": "string", "enum": registry.TIMESERIES_PROGRAMS},
            "site": {"type": "string", "description": "사업장 이름, 예: (가상)A사"},
            "n": {"type": "integer", "minimum": 1, "maximum": 30}},
            "required": ["program"]}}}, tool_get_recent_records),
    ({"type": "function", "function": {
        "name": "calc_deadline",
        "description": "기준일 + 일수 = 기한과 오늘 기준 D-day 계산 (신청 기한·정산기간 등 날짜 계산 전부).",
        "parameters": {"type": "object", "properties": {
            "base_date": {"type": "string", "description": "YYYY-MM-DD"},
            "days": {"type": "integer"}},
            "required": ["base_date", "days"]}}}, tool_calc_deadline),
] + contracts.TOOLS


def tools_for(program: str) -> tuple[list, dict]:
    """선택한 사업에 맞는 도구 집합 (공통 + 근로기준법 + 해당 사업 규칙엔진)."""
    return registry.tools_for(program, COMMON_TOOLS)


def tool_names(program: str) -> list[str]:
    return [s["function"]["name"] for s in tools_for(program)[0]]


def run_tool(name: str, raw_args: str | None, impl: dict) -> tuple[dict, object]:
    """도구 1개 실행. 인자 오류·계산 오류는 GPT 에게 error 로 돌려줘 스스로 고치게 한다."""
    try:
        args = json.loads(raw_args or "{}")
    except json.JSONDecodeError:
        return {}, {"error": "arguments JSON 파싱 실패"}
    if name not in impl:
        return args, {"error": f"unknown tool: {name}"}
    try:
        return args, impl[name](**args)
    except (TypeError, ValueError) as e:
        return args, {"error": str(e)}


TOOL_MODES = {"qa"}  # 계산 도구는 '실무 Q&A' 에만 보낸다. 온보딩·세팅 안내는 지침 설명이라 도구 없이 1회 호출로 끝낸다


def chat(system_prompt: str, history: list[dict], user_message: str, program: str = "senior",
         mode: str = "qa") -> tuple[str, list[str]]:
    """반환: (답변, 호출한 도구 목록). 도구 목록은 README '어떤 근거로 어떤 도구를 호출했는지' 근거로 화면에 표시."""
    if not is_configured():
        return NO_KEY_ANSWER, []

    from openai import BadRequestError, OpenAI, OpenAIError
    # OPENAI_BASE_URL: 교육장 게이트웨이 등 OpenAI 호환 주소. 비어 있으면 OpenAI 공식 주소 (빈 문자열이 그대로 쓰이지 않게 None 처리)
    client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None, timeout=60, max_retries=1)
    msgs: list = [{"role": "system", "content": system_prompt}]
    msgs += [{"role": m["role"], "content": m["content"]}
             for m in history if m.get("role") in ("user", "assistant")][-HISTORY_LIMIT:]
    msgs.append({"role": "user", "content": user_message})

    tools, impl = tools_for(program) if mode in TOOL_MODES else ([], {})
    t0 = time.perf_counter()
    n_calls = 0
    used: list[str] = []
    model = model_name()
    params = gen_params(model)

    def create(**kw):
        """게이트웨이가 reasoning_effort 를 거절하면(400) 빼고 다시 보내고, 이후 요청부터는 아예 보내지 않는다."""
        global _EFFORT_UNSUPPORTED
        nonlocal params, n_calls
        n_calls += 1
        if _EFFORT_UNSUPPORTED:
            params = {k: v for k, v in params.items() if k != "reasoning_effort"}
        t = time.perf_counter()
        try:
            res = client.chat.completions.create(model=model, messages=msgs, **params, **kw)
            u = getattr(res, "usage", None)
            print(f"[ai] 호출 {n_calls}: {time.perf_counter() - t:.1f}초 · 도구 {'O' if kw.get('tools') else 'X'}"
                  f" · 토큰 입력 {getattr(u, 'prompt_tokens', '?')} / 출력 {getattr(u, 'completion_tokens', '?')}")
            return res
        except BadRequestError:
            if "reasoning_effort" not in params:
                raise
            _EFFORT_UNSUPPORTED = True
            params = {k: v for k, v in params.items() if k != "reasoning_effort"}
            return client.chat.completions.create(model=model, messages=msgs, **params, **kw)

    def finish(res) -> str:
        """빈 답변을 정상처럼 보이게 하지 않는다: 비면 도구 없이 짧게 한 번 더, 그래도 비면 오류."""
        text = (res.choices[0].message.content or "").strip()
        if not text:
            msgs.append({"role": "user", "content": "위 내용을 바탕으로 지금 바로 한국어로 답변만 작성해 주세요."})
            text = (create().choices[0].message.content or "").strip()
        if not text:
            raise AIError(f"모델이 답변 본문을 만들지 못했습니다 (finish_reason={res.choices[0].finish_reason}). "
                          "AI_MODEL 을 gpt-5.4-mini 로 바꾸거나 질문을 짧게 해 보세요.")
        return knowledge.ensure_check_phrase(text)

    try:
        if not tools:  # 안내 모드: 도구 없이 1회
            answer = finish(create())
            print(f"[ai] 완료 {time.perf_counter() - t0:.1f}초 · 모델 호출 {n_calls}회 (도구 없음)")
            return answer, used
        for _ in range(MAX_TOOL_ROUNDS):
            res = create(tools=tools)
            msg = res.choices[0].message
            if not msg.tool_calls:
                answer = finish(res)
                print(f"[ai] 완료 {time.perf_counter() - t0:.1f}초 · 모델 호출 {n_calls}회 · 도구 {len(used)}개")
                return answer, used
            msgs.append(msg.model_dump(exclude_none=True))
            for tc in msg.tool_calls:
                args, result = run_tool(tc.function.name, tc.function.arguments, impl)
                used.append(f"{tc.function.name}({json.dumps(args, ensure_ascii=False)})")
                msgs.append({"role": "tool", "tool_call_id": tc.id,
                             "content": json.dumps(result, ensure_ascii=False)[:4000]})
        # 2라운드를 다 썼으면 도구 없이 마지막 답변만 받는다
        answer = finish(create())
        print(f"[ai] 완료 {time.perf_counter() - t0:.1f}초 · 모델 호출 {n_calls}회 · 도구 {len(used)}개")
        return answer, used
    except OpenAIError as e:
        raise AIError(f"{type(e).__name__}: {str(e)[:200]}") from e
