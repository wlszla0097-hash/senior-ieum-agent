"""routers/conversations.py — 대화 기록 창구: 저장·목록·상세(messages 전체)·삭제.
목록(GET /api/conversations)은 messages를 빼고 가볍게, 상세(GET /{id})에서 전체 messages 반환 — 과제 (A) 방식.
"""
from fastapi import APIRouter, HTTPException
from models import ConversationIn
from services import db

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", status_code=201)
def create_conversation(body: ConversationIn):
    return db.create("conversations", body.model_dump())


@router.get("")
def list_conversations():
    rows = db.list_all("conversations")
    rows.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    return [{k: v for k, v in r.items() if k != "messages"} | {"message_count": len(r.get("messages", []))} for r in rows]


@router.get("/{conv_id}")
def get_conversation(conv_id: str):
    row = db.get("conversations", conv_id)
    if not row:
        raise HTTPException(404, "대화를 찾을 수 없습니다")
    return row


@router.delete("/{conv_id}", status_code=204)
def delete_conversation(conv_id: str):
    if not db.delete("conversations", conv_id):
        raise HTTPException(404, "대화를 찾을 수 없습니다")
