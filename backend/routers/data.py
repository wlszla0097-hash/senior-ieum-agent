"""routers/data.py — 데이터 창구: CRUD 4개 + summary 1개 (+ 보너스 statistics, export CSV, 학습용 seed).
"""
import csv
import io

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from models import DataIn, DataUpdate, Program
from services import db, summary as summary_svc

router = APIRouter(prefix="/api/data", tags=["data"])


def _sorted(rows):
    return sorted(rows, key=lambda r: (str(r.get("date")), str(r.get("program")), str(r.get("site"))))


@router.get("/summary")
def get_summary(program: Program | None = None):
    """데이터 요약 — 프롬프트 주입용. program 생략 시 전체 + 두 사업 비교(by_program)."""
    return summary_svc.build(db.list_all("data"), program)


@router.get("/statistics")
def get_statistics():
    """보너스: 월별 평균 출근(사업별). 프론트 그래프용."""
    rows = _sorted(db.list_all("data"))
    monthly: dict[str, dict[str, list[float]]] = {}
    for r in rows:
        m = str(r["date"])[:7]
        monthly.setdefault(m, {}).setdefault(r.get("program", "senior"), []).append(float(r["value"]))
    return {"months": [
        {"month": m, **{p: round(sum(v) / len(v), 2) for p, v in d.items()}} for m, d in sorted(monthly.items())
    ]}


@router.get("/export")
def export_csv(program: Program | None = None):
    """보너스: CSV 내보내기 (엑셀 한글 깨짐 방지용 BOM 포함, 파일로 다운로드)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "date", "program", "site", "value", "memo"])
    for r in _sorted(db.list_all("data")):
        if program and r.get("program") != program:
            continue
        w.writerow([r["id"], r["date"], r.get("program"), r.get("site"), r["value"], r.get("memo", "")])
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="attendance.csv"'})


@router.post("/seed")
def seed_data():
    """합성 데이터 넣기 (이미 데이터가 있으면 0건). 학습·시연용 — 전부 가명·(가상)."""
    import seed
    return {"inserted": seed.run(), "total": db.count("data"), "storage": db.backend_name()}


@router.post("", status_code=201)
def create_data(body: DataIn):
    doc = body.model_dump()
    doc["date"] = str(doc["date"])
    return db.create("data", doc)


@router.get("")
def list_data(program: Program | None = None, limit: int = Query(default=500, ge=1, le=2000)):
    rows = _sorted(db.list_all("data"))
    if program:
        rows = [r for r in rows if r.get("program") == program]
    return rows[-limit:]


@router.put("/{item_id}")
def update_data(item_id: str, body: DataUpdate):
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(422, "수정할 항목이 없습니다")
    if patch.get("date") is not None:
        patch["date"] = str(patch["date"])
    out = db.update("data", item_id, patch)
    if not out:
        raise HTTPException(404, "데이터를 찾을 수 없습니다")
    return out


@router.delete("/{item_id}", status_code=204)
def delete_data(item_id: str):
    if not db.delete("data", item_id):
        raise HTTPException(404, "데이터를 찾을 수 없습니다")
