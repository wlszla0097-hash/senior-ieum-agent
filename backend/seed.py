"""seed.py — 합성 시계열 데이터 넣기: 두 사업 × 사업장 2곳 × 영업일 91일 = 364건 (가명·(가상)만, 실제 고객 정보 금지).
평일만, 공휴일 일부 반영. 8/20 이후 (가상)A사 참여자 1명 중도 퇴사 → '감소 추세' 학습용.
실행: Firestore 모드면 `python seed.py`. 메모리 모드는 서버와 메모리를 공유해야 하므로 POST /api/data/seed 를 쓴다.
"""
import random
from datetime import date, timedelta

from services import contracts, db

SITES = {
    "senior": [("(가상)A사", 4), ("(가상)B사", 2)],       # 참여자 수
    "flexwork": [("(가상)C사", 12), ("(가상)D사", 6)],  # 선택근무 활용 근로자 수
}
HOLIDAYS = {date(2026, 6, 3), date(2026, 6, 6), date(2026, 8, 15), date(2026, 9, 24), date(2026, 9, 25), date(2026, 9, 26), date(2026, 10, 3), date(2026, 10, 9)}


def run(days: int = 130, seed: int = 7) -> int:
    contracts.seed()  # 직원(가명) 5명 — 계약 시급 조회·수정 기능용
    if db.count("data") > 0:
        return 0
    rnd = random.Random(seed)
    end = date(2026, 10, 16)
    docs = []
    for d in (end - timedelta(days=i) for i in range(days)):
        if d.weekday() >= 5 or d in HOLIDAYS:
            continue
        for program, sites in SITES.items():
            for site, headcount in sites:
                # 시니어인턴십은 8~9월에 참여자 1명 중도 퇴사 반영(감소 추세 학습용)
                hc = headcount - (1 if program == "senior" and site == "(가상)A사" and d >= date(2026, 8, 20) else 0)
                absent = sum(1 for _ in range(hc) if rnd.random() < 0.08)
                value = max(0, hc - absent)
                memo = ""
                if absent:
                    memo = f"결근 {absent}명(사유 미기재)" if rnd.random() < 0.5 else f"연차 {absent}명"
                if program == "flexwork" and rnd.random() < 0.15:
                    memo = (memo + " / " if memo else "") + "선택근무 시차출근 활용"
                docs.append({"date": str(d), "value": value, "memo": memo, "program": program, "site": site})
    return db.bulk_create("data", docs)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    print(f"{run()}건 입력 완료 (저장소: {db.backend_name()})")
