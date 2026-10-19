"""services/db.py — 저장소 한 곳: Firestore ↔ 메모리 자동 전환 (다른 파일은 Firestore를 직접 만지지 않고 이 함수들만 호출).
- FIREBASE_SERVICE_ACCOUNT_JSON(JSON 문자열 또는 파일 경로)이 있으면 Firestore (컬렉션 data / conversations / employees)
- 없거나 초기화에 실패하면 메모리(dict) — 로컬 학습용. 서버를 끄면 사라진다. 실패 사유는 GET / 의 storage 에 표시.
"""
import json
import os
import uuid
from datetime import datetime, timezone

_db = None
_init_error: str | None = None   # Firestore 초기화 실패 사유 (한 번만 시도)
_mem: dict[str, dict] = {"data": {}, "conversations": {}, "employees": {}}  # 컬렉션 3개 (Firestore 와 같은 이름)


def _firestore():
    global _db, _init_error
    if _db is not None or _init_error is not None:
        return _db
    raw = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        if raw.startswith("{"):
            info = json.loads(raw)
        else:
            with open(raw, encoding="utf-8") as f:
                info = json.load(f)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(info))
        _db = firestore.client()
    except Exception as e:  # noqa: BLE001 — 키 형식 오류 등은 메모리 모드로 계속 동작
        _init_error = type(e).__name__
        print(f"[db] Firestore 초기화 실패 → 메모리 모드로 전환: {_init_error}")
    return _db


def backend_name() -> str:
    if _firestore():
        return "firestore"
    return f"memory (firebase 초기화 실패: {_init_error})" if _init_error else "memory"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- 공통 CRUD (collection = "data" | "conversations") ----------

def create(collection: str, doc: dict) -> dict:
    now = _now()
    doc = {**doc, "created_at": now, "updated_at": now}
    db = _firestore()
    if db:
        ref = db.collection(collection).document()
        ref.set(doc)
        return {"id": ref.id, **doc}
    _id = uuid.uuid4().hex[:12]
    _mem[collection][_id] = doc
    return {"id": _id, **doc}


def list_all(collection: str) -> list[dict]:
    db = _firestore()
    if db:
        return [{"id": d.id, **d.to_dict()} for d in db.collection(collection).stream()]
    return [{"id": k, **v} for k, v in _mem[collection].items()]


def get(collection: str, _id: str) -> dict | None:
    db = _firestore()
    if db:
        snap = db.collection(collection).document(_id).get()
        return {"id": snap.id, **snap.to_dict()} if snap.exists else None
    v = _mem[collection].get(_id)
    return {"id": _id, **v} if v else None


def update(collection: str, _id: str, patch: dict) -> dict | None:
    patch = {k: v for k, v in patch.items() if v is not None}
    patch["updated_at"] = _now()
    db = _firestore()
    if db:
        ref = db.collection(collection).document(_id)
        if not ref.get().exists:
            return None
        ref.update(patch)
        return {"id": _id, **ref.get().to_dict()}
    if _id not in _mem[collection]:
        return None
    _mem[collection][_id].update(patch)
    return {"id": _id, **_mem[collection][_id]}


def delete(collection: str, _id: str) -> bool:
    db = _firestore()
    if db:
        ref = db.collection(collection).document(_id)
        if not ref.get().exists:
            return False
        ref.delete()
        return True
    return _mem[collection].pop(_id, None) is not None


def count(collection: str) -> int:
    db = _firestore()
    if db:
        try:  # 집계 쿼리: 문서를 다 읽지 않고 개수만 (읽기 비용 절약)
            return int(db.collection(collection).count().get()[0][0].value)
        except Exception:  # noqa: BLE001 — 구버전 SDK 등에서는 전체 조회로 대체
            return len(list_all(collection))
    return len(_mem[collection])


def bulk_create(collection: str, docs: list[dict]) -> int:
    """여러 건을 한 번에 저장 (seed 용). Firestore 는 500건 단위 batch 로 왕복 횟수를 줄인다."""
    db = _firestore()
    if not db:
        for d in docs:
            create(collection, d)
        return len(docs)
    now = _now()
    for i in range(0, len(docs), 500):
        batch = db.batch()
        for d in docs[i:i + 500]:
            batch.set(db.collection(collection).document(), {**d, "created_at": now, "updated_at": now})
        batch.commit()
    return len(docs)
