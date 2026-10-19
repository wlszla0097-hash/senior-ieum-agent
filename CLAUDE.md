# senior-ieum-agent — Claude Code 작업 규칙

## 이 프로젝트는
코디세이 과제 "AI Agent 개발: 나만의 AI 비서 구축" 제출물.
시니어인턴십(복지부)·선택근무제 일생활균형지원금(고용부) 운영 담당자를 위한 '선임자 역할' 교육·컨설팅 AI 비서.
요구사항·구조·학습 순서는 README.md 가 기준. 작업 전에 README.md 를 먼저 읽는다.

## 고정 조건 (바꾸지 않는다)
- 백엔드 FastAPI / DB Firestore / AI OpenAI / 프론트 바닐라 HTML·CSS·JS / 배포 Render(백엔드)+Vercel(프론트)
- 패키지는 fastapi, uvicorn, firebase-admin, openai, python-dotenv 5개만. 추가하려면 먼저 물어본다
- 저장은 services/db.py 한 곳만 거친다. AI 호출은 services/ai.py 한 곳만. 계약 시급 조회·수정은 services/contracts.py 한 곳만
- 사업별 지식·규칙엔진은 backend/programs/<id>/ 에. 새 사업은 폴더 추가 + programs/registry.py 한 줄 (README '새 사업 추가하는 법')
- AI: 교육장 OpenAI 호환 게이트웨이(OPENAI_BASE_URL=https://copa.codyssey.kr/v1), AI_MODEL=gpt-5-mini (gpt-5 계열은 추론 모델 — services/ai.py 가 max_completion_tokens·reasoning_effort 로 자동 전환)
- 비용 통제: 최근 10개 메시지, 도구 호출 2라운드, 추론 모델 max_completion_tokens 4000·reasoning_effort low. 늘리려면 먼저 물어본다
- 빈 답변을 고지 문구로 덮지 않는다 — 비면 재시도 후 오류로 표시

## 원칙
- AI는 설명만, 날짜·금액·충족 여부는 규칙엔진(programs/*/rules.py, programs/common/labor.py), 최종 결정은 사람. 법적 판단(적법/위법)·수치 추정 금지
- 시급은 우리가 산정하지 않는다: 근로계약서 기재값 또는 담당자 수정값을 출처·이력(wage_history)과 함께 쓴다. 수정 사유·수정자 필수
- 모든 계산 결과에 formula·basis·warnings·wage_source·disclaimer 를 붙인다 (labor.DISCLAIMER 문구 고정)
- 지침 수치는 programs/<id>/knowledge.py 한 곳에서 관리. verified=True 는 한국노인인력개발원 사업소개로 확인된 값,
  선택근무제는 DOl 검토 2026 운영 기준(월 6시간 이상 단축·월 30만원·연 360만원). False(⚠)는 원문이 있어야 아는 값만. 원문 없이 ⚠ 를 지우지 않는다
- 비서는 회피하지 않는다: 확인된 기준값은 구체적으로 안내하고, ⚠ 항목을 언급할 때만 '지침 원문 확인 필요'를 붙인다
- 시연 데이터는 가명·(가상)만. 실제 고객·근로자 정보, API 키 값은 코드·문서·커밋·대화에 넣지 않는다
- .env 는 커밋하지 않는다 (.gitignore 에 있음). .env.example 만 갱신한다
- 이 폴더 밖(이음24, Senior_ieum 등 다른 프로젝트)은 건드리지 않는다

## 작업 방식
- 수정 전에 무엇을 왜 바꾸는지 한 줄로 말하고, 끝나면 바뀐 파일 목록을 보고한다
- 구조 변경·새 파일·비용이 생기는 기능은 하기 전에 물어본다
- 코드를 바꾸면 반드시 로컬에서 실행해 확인한다:
  cd backend && uvicorn main:app --reload  → http://localhost:8000/docs
  확인 항목: POST /api/data/seed, GET /api/data/summary, CRUD, POST /api/chat, conversations 저장·불러오기, 잘못된 입력 422
- 프론트는 frontend 폴더를 5500 포트 정적 서버로 열어 네 화면(채팅/데이터/대화기록/요약) 확인
- 사용자는 비전공자다. 설명은 짧게, 용어는 README 9·11장 수준으로

## 자주 쓰는 명령 (Windows)
- 가상환경: cd backend && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
- 서버: uvicorn main:app --reload
- 프론트 빌드 확인: node frontend/build.js
