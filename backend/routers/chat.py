"""routers/chat.py — AI 채팅 창구: ① 데이터 요약 조회 → ② 시스템 프롬프트에 삽입 → ③ GPT 호출 → ④ conversations 자동 저장.
학습용으로 GET /api/chat/prompt-preview 가 ①②까지만 실행해 실제 시스템 프롬프트를 보여준다 (키 소모 없음).
"""
from fastapi import APIRouter, HTTPException
from models import ChatIn, ChatProgram, Mode
from services import ai, db, knowledge, summary as summary_svc

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _build_prompt(program: str, mode: str) -> tuple[str, dict]:
    # ① 요약: 시계열이 있는 사업은 그 사업만, HR 공통 탭은 전체(두 사업 비교)
    s = summary_svc.build(db.list_all("data"), program if program in summary_svc.PROGRAM_LABEL else None)
    try:
        return knowledge.system_prompt(program, mode, summary_svc.to_prompt_text(s)), s   # ② 프롬프트
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@router.post("")
def chat(body: ChatIn):
    prompt, s = _build_prompt(body.program, body.mode)

    # 이어지는 대화면 기존 기록을 불러온다
    conv = db.get("conversations", body.conversation_id) if body.conversation_id else None
    if body.conversation_id and not conv:
        raise HTTPException(404, "대화를 찾을 수 없습니다")
    history = conv.get("messages", []) if conv else []

    # ③ GPT (키 없으면 안내 문구, 호출 실패면 502 — 실패한 답변은 저장하지 않는다)
    try:
        answer, tools_used = ai.chat(prompt, history, body.message, body.program, body.mode)
    except ai.AIError as e:
        raise HTTPException(502, f"AI 호출 실패 — {e}") from e

    # ④ 자동 저장
    messages = history + [{"role": "user", "content": body.message}, {"role": "assistant", "content": answer}]
    if conv:
        db.update("conversations", conv["id"], {"messages": messages, "program": body.program, "mode": body.mode})
        conv_id = conv["id"]
    else:
        title = body.message[:30] + ("…" if len(body.message) > 30 else "")
        conv_id = db.create("conversations", {"title": title, "program": body.program, "mode": body.mode,
                                              "messages": messages})["id"]

    return {"conversation_id": conv_id, "answer": answer, "tools_used": tools_used,
            "ai_configured": ai.is_configured(), "summary_used": s}


@router.get("/prompt-preview")
def prompt_preview(program: ChatProgram = "senior", mode: Mode = "qa"):
    """학습용: 실제로 GPT에 들어가는 시스템 프롬프트와 비용 통제 설정을 그대로 보여준다 (키 소모 없음)."""
    prompt, _ = _build_prompt(program, mode)
    return {
        "system_prompt": prompt,
        "chars": len(prompt),
        "settings": {"model": ai.model_name(), "max_tokens": ai.gen_params(ai.model_name()).get("max_completion_tokens", ai.MAX_TOKENS), "history_limit": ai.HISTORY_LIMIT,
                     "max_tool_rounds": ai.MAX_TOOL_ROUNDS, "tools": ai.tool_names(program) if mode in ai.TOOL_MODES else []},
    }
