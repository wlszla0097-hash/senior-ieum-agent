"""services/summary.py — 시계열 분석: 출근 기록 목록 → 요약(기간·건수·평균/최대/최소·최근 30일 추세·사업장별 평균).
이 결과가 to_prompt_text() 로 글이 되어 시스템 프롬프트에 들어간다 (컨텍스트 주입).
"""
from datetime import date, timedelta
from statistics import mean

PROGRAM_LABEL = {"senior": "시니어인턴십(보건복지부)", "flexwork": "일생활균형 선택근무제(고용노동부)"}


def _trend(rows: list[dict]) -> str:
    """최근 30일 평균 vs 그 이전 기간 평균으로 증가/감소/유지 판단. (rows 는 날짜순 정렬 상태)"""
    if len(rows) < 10:
        return "판단 보류 (데이터 10건 미만)"
    last = date.fromisoformat(str(rows[-1]["date"])[:10])
    cut = (last - timedelta(days=30)).isoformat()
    recent = [float(r["value"]) for r in rows if str(r["date"])[:10] > cut]
    before = [float(r["value"]) for r in rows if str(r["date"])[:10] <= cut]
    if not recent or not before or mean(before) == 0:
        return "판단 보류 (비교 기간 부족)"
    pct = (mean(recent) - mean(before)) / mean(before) * 100
    label = "증가" if pct > 5 else "감소" if pct < -5 else "유지"
    return f"{label} (최근 30일 평균 {mean(recent):.1f} vs 이전 {mean(before):.1f}, {pct:+.1f}%)"


def _summarize(rows: list[dict]) -> dict:
    rows = sorted(rows, key=lambda r: str(r.get("date")))
    if not rows:
        return {"period": "-", "count": 0, "metrics": {}, "trend": "데이터 없음", "sites": []}
    values = [float(r.get("value", 0)) for r in rows]
    sites = sorted({r.get("site", "") for r in rows})
    by_site = {s: round(mean([v for v, r in zip(values, rows) if r.get("site") == s]), 1) for s in sites}
    return {
        "period": f"{rows[0]['date']} ~ {rows[-1]['date']}",
        "count": len(rows),
        "metrics": {
            "total": round(sum(values), 1),
            "average": round(mean(values), 2),
            "max": max(values),
            "min": min(values),
            "zero_days": sum(1 for v in values if v == 0),  # 출근 0명인 날 = 결근/휴무 점검 대상
        },
        "trend": _trend(rows),
        "sites": sites,
        "site_average": by_site,
    }


def build(rows: list[dict], program: str | None = None) -> dict:
    """program 지정 시 그 사업만, 없으면 전체 + 사업별 비교."""
    if program:
        s = _summarize([r for r in rows if r.get("program") == program])
        s["program"] = program
        s["program_label"] = PROGRAM_LABEL.get(program, program)
        return s
    out = _summarize(rows)
    out["by_program"] = {
        p: _summarize([r for r in rows if r.get("program") == p]) for p in PROGRAM_LABEL
    }
    return out


def to_prompt_text(s: dict) -> str:
    """요약 dict → 프롬프트에 넣을 짧은 텍스트 (1KB 안팎으로 토큰 절약)."""
    lines = [
        f"- 사업: {s.get('program_label', '전체(두 사업 비교)')}",
        f"- 데이터 기간: {s['period']} / 레코드 {s['count']}건",
        (f"- 지표(사업장·일자별 출근 인원): 평균 {m['average']}명, 최대 {m['max']:g}명, 최소 {m['min']:g}명, "
         f"출근 0명인 날 {m['zero_days']}건" if (m := s["metrics"]) else "- 지표: 없음"),
        f"- 최근 추세: {s['trend']}",
    ]
    if s.get("site_average"):
        lines.append(f"- 사업장별 평균 출근: {s['site_average']}")
    if s.get("by_program"):
        for p, ps in s["by_program"].items():
            lines.append(f"- [{PROGRAM_LABEL[p]}] {ps['count']}건, 평균 {ps['metrics'].get('average')}, 추세 {ps['trend']}")
    return "\n".join(lines)
