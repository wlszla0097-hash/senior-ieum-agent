# 시니어 이음 AI 비서 (Senior_ieum Agent)

> 코디세이 과제 "AI Agent 개발: 나만의 AI 비서 구축" 제출물
> 시니어인턴십(보건복지부)·선택근무제 일생활균형 지원금(고용노동부)을 **처음 맡은 담당자·기관**에게 교육·컨설팅을 해 주는 **선임자 역할 AI 비서**

## 1. 서비스 소개 — 무엇을 해결하나

정부 고용지원사업을 처음 맡은 **신입 담당자·신규 운영기관**은 물어볼 선임자가 없으면 지침·서류·신청 시기를 혼자 찾아야 한다.
이 서비스는 시스템 프롬프트에 세 가지를 넣는다. ① 기관의 **출근 기록 시계열 요약**, ② 사업별 **지침 기준값**, ③ **선임자 체크리스트**. 이렇게 해서 "우리 기관 상황을 아는" 교육·컨설팅 답변을 만든다.

- **비서 모드 3가지**: 신규 담당자 온보딩 / 신규 기관 세팅 컨설팅 / 실무 Q&A
- **사업 2가지**(`senior`, `flexwork`)를 같은 데이터 모델 `(date, value, memo, program, site)`로 다룬다. 그래서 **사업 간 출근 현황 비교**가 된다 (요약·그래프·도구).
- **원칙**: AI는 설명만 한다. 날짜·금액은 **규칙엔진**(도구 호출)이 계산하고, 최종 결정은 사람이 한다. 법적 판단을 하지 않고, 모르는 수치를 추정하지 않는다.
- **⚠ 표시**: 지침 수치 중 2026 원문으로 확인하지 않은 값에는 ⚠를 붙인다. 답변에는 항상 "지침 원문 확인 필요"가 들어간다. GPT가 빠뜨리면 서버가 붙인다.
- 시연 데이터는 전부 합성 데이터다(가명·(가상)). 실제 고객·개인정보는 넣지 않는다.

## 2. 기술 스택 (과제 지정 구성, 패키지 5개만)

| 구분 | 사용 | 한 줄 설명 |
|---|---|---|
| 백엔드 | **FastAPI** + uvicorn (Python 3.10+) | API 창구. `/docs` 에 Swagger 자동 생성 |
| 검증 | **Pydantic** (`models.py`) | 신청서 양식. 틀린 입력은 422로 자동 거절 |
| DB | **Firebase Firestore** (`services/db.py`) | 컬렉션 `data`, `conversations`, `employees`. 키가 없으면 메모리 모드로 자동 전환 |
| AI | **OpenAI GPT** (`services/ai.py`) | gpt-4o-mini, max_tokens 700, Function Calling — 사업별로 도구 8~9개 (registry 가 모아 줌) |
| 프론트 | HTML / CSS / Vanilla JS | 프레임워크 없음. 그래프도 `<canvas>` 로 직접 그림 |
| 배포 | 백엔드 **Render**, 프론트 **Vercel** (+ 비교용으로 백엔드를 Vercel 에도) | |

`requirements.txt`: `fastapi`, `uvicorn`, `firebase-admin`, `openai`, `python-dotenv` (그 외는 표준 라이브러리만)

### 폴더 구조 — 파일 하나 = 역할 하나 (모든 파일 첫 줄에 역할 주석, 단 JSON 은 주석 문법이 없어 예외)

```
backend/
  main.py                   앱 시작, CORS, 라우터 연결, 상태 확인(GET /)
  models.py                 Pydantic 양식 (DataIn, ChatIn, WageUpdate, OvertimeIn …)
  routers/data.py           /api/data  CRUD + summary (+statistics, export, seed)
  routers/conversations.py  /api/conversations  저장·목록·상세·삭제
  routers/chat.py           /api/chat  요약→프롬프트→GPT→자동 저장, prompt-preview
  routers/programs.py       /api/programs  사업(탭) 목록
  routers/employees.py      /api/employees  계약 시급 조회·담당자 수정(이력 누적)
  routers/labor.py          /api/labor/*  연장·최저임금·주휴·선택근무 점검 (화면용)
  services/db.py            Firestore ↔ 메모리 저장소 (DB는 이 파일만 거침)
  services/summary.py       시계열 분석 → 요약(기간·건수·평균/최대/최소·최근 30일 추세)
  services/knowledge.py     프롬프트 조립 (얇은 층) + 공통 원칙
  services/contracts.py     근로계약서 기재 시급 조회·수정 이력 (추후 이음24 읽기 API 로 교체할 자리)
  services/ai.py            OpenAI 호출 + 도구 호출 루프 + 비용 통제
  programs/registry.py      ★ 등록된 사업 목록 — 탭·모드·빠른 질문·도구가 여기서 나온다
  programs/senior/          시니어인턴십: knowledge.py(지침·체크리스트) rules.py(신청 일정·지원액 규칙엔진)
  programs/flexwork/        선택근무제: knowledge.py  rules.py(정산기간 점검)
  programs/common/          HR 공통: knowledge.py(채용 후 세팅 안내) labor.py(연장·야간·휴일·최저임금·주휴 계산)
  seed.py                   합성 데이터 364건 + 직원(가명) 5명
  requirements.txt  .env.example
api/index.py                Vercel 용 입구 (같은 FastAPI 앱 import)
vercel.json  requirements.txt   백엔드 Vercel 배포 설정
render.yaml                 Render Blueprint
frontend/
  index.html  app.js  style.css   사업 탭 · 채팅 · HR 공통 계산 · 요약/그래프 · 데이터 관리 · 대화 기록
  config.js                 백엔드 주소를 정하는 단 한 곳
  build.js                  Vercel 빌드: API_BASE_URL 을 config.js 에 구워 dist/ 생성
  vercel.json               프론트 Vercel 설정 (node build.js → dist)
```

### 새 사업(탭) 추가하는 법

1. `backend/programs/<id>/knowledge.py` 를 만든다 — `ID, LABEL, LABEL_LONG, RULES, MODES, QUICK_QUESTIONS` (senior 폴더를 복사해 내용만 바꾸면 된다)
2. 날짜·금액 계산이 있으면 같은 폴더에 `rules.py` 를 만들고 `TOOLS = [(OpenAI 함수 스키마, 구현 함수)]` 를 둔다
3. `backend/programs/registry.py` 의 `PROGRAMS` 에 한 줄 추가 → 프론트 탭·모드·빠른 질문·AI 도구에 자동 반영
4. 시계열 데이터를 쓰는 사업이면 `models.py` 의 `Program`, `ChatProgram` 에 id 를 추가

### 데이터 구조

```
data:           { date "YYYY-MM-DD", value 출근 인원(명), memo, program senior|flexwork, site 사업장(가명), created_at, updated_at }
conversations:  { title, program senior|flexwork|hr, mode onboarding|setup|qa, messages:[{role, content}], created_at, updated_at }
employees:      { employee_id, name(가명), site, program, hourly_wage 계약 시급, weekly_contract_hours, daily_hours, contract_date,
                  wage_history:[{before, after, reason, edited_by, edited_at}] }   ← 담당자가 수정해도 원값은 남는다
```

시계열 데이터는 사업장별·일자별 출근 인원이다(합성). 두 사업 × 사업장 2곳 × 영업일 91일 = **364건**. 2026-08-20부터 (가상)A사 참여자 1명이 중도 퇴사하도록 넣어 두어서 시니어인턴십 쪽에 **감소 추세**가 보인다.

## 3. 배포 URL

| 구분 | URL |
|---|---|
| 프론트 (Vercel) | https://________.vercel.app |
| 백엔드 API (Render) | https://________.onrender.com |
| Swagger (Render) | https://________.onrender.com/docs |
| 백엔드 비교용 (Vercel) | https://________.vercel.app/docs |

(배포 후 채워 넣기)

## 4. 로컬 실행 (Firebase·OpenAI 키 없이도 됨)

**백엔드** (Windows PowerShell 기준, mac/linux 는 주석 참고)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate                 # mac/linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                 # mac/linux: cp .env.example .env
uvicorn main:app --reload              # → http://localhost:8000/docs
```

**프론트** (새 터미널)

```powershell
cd frontend
python -m http.server 5500             # 또는 VS Code Live Server(5500)
```

http://localhost:5500 을 연다 → 오른쪽 "샘플 넣기" → 요약·그래프·표 확인 → 채팅에서 "첫 달 할 일" (키가 없으면 `[AI 미설정]` 안내가 나오고 대화는 저장된다).

- 상단 표시 `연결됨 · 저장소 memory · AI 미설정` 은 메모리 모드이고 OpenAI 키가 없다는 뜻이다. 서버를 끄면 데이터가 사라진다.
- "프롬프트 보기" 버튼이나 `GET /api/chat/prompt-preview?program=senior&mode=onboarding` 으로 **GPT에 실제로 들어가는 시스템 프롬프트**를 볼 수 있다 (키 소모 없음).
- 다른 백엔드로 테스트하려면 프론트 주소 뒤에 `?api=https://백엔드주소` 를 붙인다 (브라우저가 기억한다). 되돌리려면 `?api=reset`.

### 단계별 학습 순서

1. **메모리 모드**: 위 로컬 실행 → Swagger 에서 `POST /api/data/seed` → `GET /api/data/summary` → CRUD → 일부러 `"date": "2026/10/17"`, `"value": -1` 을 보내 **422** 확인
2. **Firestore 연결**: Firebase 콘솔 → 프로젝트 생성 → Firestore Database 생성 → 프로젝트 설정 → 서비스 계정 → *새 비공개 키 생성*. 받은 JSON 을 `.env` 의 `FIREBASE_SERVICE_ACCOUNT_JSON=` 에 **한 줄로** 붙여넣는다 (또는 파일 경로, 파일은 `.gitignore` 대상 이름으로). 재시작하면 `GET /` 의 `storage` 가 `firestore` 로 바뀐다 → seed → 콘솔에서 364건 확인 → 서버를 재시작해도 데이터가 남는지 확인
3. **OpenAI 연결**: 키를 발급하고 **월 사용 한도를 먼저 설정**(예: $5) → `.env` 의 `OPENAI_API_KEY=` → 채팅 "신청 일정 계산" 버튼 → 답변 아래 `도구 호출: calc_senior_schedule(...)` 표시 확인
4. **배포**: 아래 9장 순서대로

## 5. 환경 변수

| 변수 | 어디에 | 용도 | 없으면 |
|---|---|---|---|
| `OPENAI_API_KEY` | 백엔드 | GPT 호출 | 채팅만 `[AI 미설정]` 안내, 나머지 기능은 정상 |
| `AI_MODEL` | 백엔드 | 기본 `gpt-4o-mini` | gpt-4o-mini |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | 백엔드 | 서비스 계정 JSON 내용(한 줄) 또는 파일 경로 | 메모리 저장소 (키 형식이 틀려도 메모리로 전환, `GET /` 에 사유 표시) |
| `ALLOWED_ORIGINS` | 백엔드 | CORS 허용 프론트 주소, 쉼표 구분 | `*` (학습용) |
| `SENIOR_API_URL` | 백엔드(선택) | 외부 Senior_ieum 규칙엔진 주소 | 내장 규칙엔진 `programs/senior/rules.py` 사용 |
| `PYTHON_VERSION` | Render | `render.yaml` 에 3.12.8 지정 | Render 기본값 |
| `API_BASE_URL` | 프론트(Vercel 빌드) | 백엔드 주소. `build.js` 가 `config.js` 에 굽는다 | `http://localhost:8000` |

키 값은 `.env` 와 배포 대시보드에만 둔다. `.env` 는 `.gitignore` 대상이고 `.env.example` 만 커밋한다. 저장소·스크린샷·대화에 키를 노출하지 않는다.

## 6. API 목록

| 메서드 | 경로 | 역할 |
|---|---|---|
| GET | `/` | 상태 (저장소·AI 설정 여부, 키 값은 노출 안 함) |
| POST / GET | `/api/data` | 추가 / 목록 (`?program=`, `?limit=`) |
| PUT / DELETE | `/api/data/{id}` | 수정(바꿀 항목만) / 삭제 |
| GET | `/api/data/summary` | 요약: 기간·건수·평균/최대/최소·최근 30일 추세·사업장별 평균 (`?program=` 생략 시 두 사업 비교 `by_program`) |
| GET | `/api/data/statistics` | 보너스: 사업별 월별 평균 (그래프용) |
| GET | `/api/data/export` | 보너스: CSV 다운로드 (엑셀 한글 호환 BOM) |
| POST | `/api/data/seed` | 학습용: 합성 데이터 364건 (데이터가 있으면 0건) |
| POST / GET | `/api/conversations` | 저장 / 목록 (messages 제외, `message_count` 포함) |
| GET / DELETE | `/api/conversations/{id}` | 상세 (messages 전체) / 삭제 |
| POST | `/api/chat` | 요약 → 프롬프트 → GPT(도구 호출) → 자동 저장 |
| GET | `/api/chat/prompt-preview` | 학습용: 실제 시스템 프롬프트 + 비용 통제 설정 + 사업별 도구 목록 보기 |
| GET | `/api/programs` | 사업(탭) 목록 — 모드·빠른 질문·도구 이름 |
| GET | `/api/employees`, `/api/employees/{id}` | 직원(가명) 목록 / 상세 — 계약 시급·출처·수정 이력 |
| PUT | `/api/employees/{id}/wage` | 담당자 시급 수정 — `{hourly_wage, reason(5자 이상), edited_by}` 필수, 이력 누적 |
| POST | `/api/labor/overtime` | 연장·야간·휴일 가산수당 (제56조) — `employee_id` 또는 `hourly_wage`+`weekly_contract_hours` |
| POST | `/api/labor/min-wage` | 최저임금 비교 (경고만, 판정 아님) |
| POST | `/api/labor/weekly-holiday` | 주휴 발생 여부·시간·수당 (제55조) |
| POST | `/api/labor/flexwork-check` | 선택근무제 정산기간 점검 — 주별 시간 목록 → 항목별 충족/미충족 |

## 7. 컨텍스트 주입 흐름 (과제 핵심)

```
사용자 질문 ─► routers/chat.py
   ① services/summary.build()          출근 기록 → {기간, 건수, 평균/최대/최소, 최근 30일 추세, 사업장별 평균}
   ② services/knowledge.system_prompt() 요약 + 지침 기준값(⚠) + 선임자 체크리스트 + 공통 원칙 → 시스템 프롬프트
   ③ services/ai.chat()                GPT 호출 → 필요하면 도구 호출(최대 2라운드) → 최종 답변
                                        + knowledge.ensure_check_phrase(): '지침 원문 확인 필요' 보장
   ④ services/db.create/update          conversations 에 자동 저장 (AI 호출 실패 시 저장하지 않고 502)
 ◄─ { answer, tools_used, conversation_id, summary_used }
```

**비용 통제**: 모델 `gpt-4o-mini`, `max_tokens` 700, 최근 10개 메시지만 전송, 도구 호출 최대 2라운드, 도구 결과 4,000자 제한, 요청 timeout 30초·재시도 1회. 키가 없으면 OpenAI 를 아예 호출하지 않는다.

### 보너스 · Function Calling: 어떤 근거로 어떤 도구를 부르나

| 도구 | GPT가 호출하는 상황 | 근거 |
|---|---|---|
| `get_data_summary(program?)` | "두 사업 비교"처럼 프롬프트의 요약(선택한 사업만)으로는 부족할 때 | 프롬프트는 토큰을 아끼려고 선택한 사업 요약만 담는다 |
| `get_recent_records(program, site?, n)` | "최근 결근 사유", "A사 지난주"처럼 개별 기록이 필요할 때 | 요약에는 개별 행·메모가 없다 |
| `calc_senior_schedule(start_date, monthly_wage, hire_type)` | "6월 1일 시작한 인턴 신청 마감일·지원액은?" | **원칙 3**: 날짜·금액은 AI가 아니라 규칙엔진이 계산. 미확인 수치를 쓰면 결과에 ⚠ `warnings` |
| `calc_deadline(base_date, days)` | "기준일부터 30일 뒤가 언제? D-day는?" (모든 날짜 계산) | 같은 원칙. 주말·공휴일 연장 여부는 지침 확인 안내 |
| `get_contract_wage(employee_id)` / `list_employees()` | 금액 계산 전에 시급이 필요할 때 | 시급은 AI·우리가 정하지 않고 **근로계약서 기재값(기업 입력)** 또는 **담당자 수정값**을 출처·이력과 함께 쓴다 |
| `calc_overtime(...)` | "E001 연장 5시간 야간 2시간 수당은?" | 근로기준법 제56조. 결과에 계산식·조문·`wage_source`·⚠·고지 문구. 5인 미만이면 적용/미적용 두 금액 |
| `check_min_wage(hourly_wage, year)` | "이 시급 최저임금 맞아?" | 경고만, 적법/위법 판정 없음 |
| `calc_weekly_holiday(weekly_contract_hours, ...)` | "주 20시간 주휴는?" | 제55조·제18조 3항 |
| `check_flexwork(weekly_hours, core_hours_met)` (선택근무제 탭) | "정산기간 4주 38/42/40/39h 점검" | 제52조. 항목별 충족/미충족 목록, 판정 아님 |

**도구는 탭(사업)마다 다르다**: 공통(데이터·날짜·계약·근로기준법) + 선택한 사업의 규칙엔진만 GPT 에 넘긴다 (`programs/registry.tools_for`).

### 책임 경계 — 안내·계산만, 판정 없음

| 하는 것 | 안 하는 것 |
|---|---|
| 조문 인용 + 계산식 표시 + 금액 | "위법/적법" 단정, 법적 자문 |
| 계약서 시급을 **출처 기록**과 함께 사용 (원값→수정값·사유·수정자) | 시급·통상임금을 우리가 산정하거나 추정 |
| ⚠ 경고와 "노무사·고용센터 확인" 안내 | 지원 가능 여부 확정 |

- 모든 계산 응답에 `disclaimer` 고정 문구가 들어가고 화면 결과 카드 맨 아래에 항상 표시된다.
- HR 공통 탭은 **책임 한정 동의** 체크 전에는 계산 버튼이 비활성이다 (동의 여부는 브라우저에 기억).
- 담당자가 시급을 수정하면 `reason`(5자 이상)·`edited_by` 가 필수이고 원값은 지우지 않는다 — "누가 언제 왜 바꿨는지"가 결과에 남는다.

호출 결과는 응답의 `tools_used` 와 채팅 화면 답변 아래 "도구 호출:" 줄에 표시된다.
`SENIOR_API_URL` 이 있으면 `calc_senior_schedule` 은 외부 규칙엔진을 먼저 부르고, 실패하면 내장 엔진으로 대체한다.

## 8. 보너스 구현 현황

| 보너스 | 구현 |
|---|---|
| Function Calling | 사업별 도구 8~9개, 최대 2라운드 (`services/ai.py` + `programs/registry.py`) |
| `/api/data/statistics` | 사업별 월별 평균 |
| 그래프 | 오른쪽 패널 월별 평균 출근 꺾은선 (canvas, 다크 모드 색 반영) |
| CSV 내보내기 | "CSV" 버튼 → `attendance.csv` |
| 다크 모드 | 🌙/☀️ 버튼, OS 설정을 따르고 선택을 기억 |

## 9. 배포 순서

**Render (백엔드)**
1. GitHub 에 push (`.env`·서비스 계정 JSON 이 올라가지 않았는지 `git status` 로 확인)
2. Render → New → **Blueprint** → 저장소 선택 (`render.yaml` 이 rootDir `backend`, build/start 명령, Python 3.12.8 을 채운다)
3. Environment 에 `OPENAI_API_KEY`, `FIREBASE_SERVICE_ACCOUNT_JSON`(한 줄 JSON), `ALLOWED_ORIGINS` 를 입력한다 (Vercel 주소는 다음 단계 후 추가)
4. `https://….onrender.com/docs` 확인. 무료 티어는 15분 동안 쓰지 않으면 잠들어 첫 응답이 30초쯤 걸린다. 프론트는 3초가 넘으면 안내 문구를 띄운다

**Vercel (프론트)**
1. Add New Project → 같은 저장소 → **Root Directory `frontend`** (`frontend/vercel.json` 이 Build `node build.js`, Output `dist` 를 지정)
2. Environment Variables: `API_BASE_URL` = Render 백엔드 주소
3. 배포 후 프론트 주소를 Render 의 `ALLOWED_ORIGINS` 에 추가하고 저장(재배포). 이걸 빠뜨리면 CORS 오류가 난다
4. 상단이 "연결됨 · 저장소 firestore · AI 설정됨" 인지 확인

**Vercel (백엔드 비교용)**
1. Add New Project → 같은 저장소, Root Directory 는 **비워 둔다** (루트 `vercel.json` + `api/index.py` + 루트 `requirements.txt`)
2. 같은 환경 변수 입력 → `https://….vercel.app/docs` 확인
3. 프론트 주소 뒤에 `?api=https://….vercel.app` 을 붙여 Render 와 번갈아 비교한다 (`?api=reset` 으로 복귀)

| 비교 항목 | Render (항상 켜진 서버) | Vercel (서버리스 함수) |
|---|---|---|
| 첫 응답 | 잠들면 ~30초 | 콜드스타트 1~3초 |
| 실행 시간 한도 | 없음 | 플랜별 제한 (도구 2라운드 채팅이 길면 주의) |
| 상태 유지 | 메모리 유지(재시작 전까지) | 요청마다 초기화될 수 있음 → **메모리 모드면 데이터가 사라지므로 Firestore 필수** |
| 과제 요구 | ✅ 지정 | 비교·학습용 |

(직접 측정한 값으로 표를 채우기)

## 10. 제출 스크린샷

`docs/screenshots/` 폴더에 넣고 아래에 링크한다.

- [ ] 채팅 화면: 질문 + 답변 + "도구 호출:" 표시 + 오른쪽 데이터 요약
- [ ] 데이터 관리 화면: 추가, 수정(Enter), 삭제 동작
- [ ] 대화 기록 화면: 목록에서 불러오기
- [ ] "프롬프트 보기" 대화상자 (컨텍스트 주입 증거)
- [ ] Swagger `/docs` (Render 주소)
- [ ] (보너스) 그래프 + 다크 모드

## 11. 평가 때 항목별 한 문장

| 평가 항목 | 한 문장 설명 |
|---|---|
| 서비스 목적 | "사업을 처음 맡은 담당자에게 선임자처럼 온보딩·기관 세팅·실무 Q&A를 해 주는 비서이고, 우리 기관 출근 데이터를 알고 답합니다." |
| FastAPI 구조 | "창구(routers)는 요청만 받고 일(services)은 따로 둬서, 저장소나 AI를 바꿔도 창구는 건드리지 않습니다." |
| Pydantic 검증 | "`models.py` 가 신청서 양식이라 날짜 형식이 틀리거나 value 가 음수면 코드에 닿기 전에 422로 거절됩니다." |
| 데이터 CRUD | "`/api/data` 에서 추가·조회·수정·삭제를 하고, 수정은 바꿀 항목만 보내면 됩니다." |
| 시계열 데이터 | "사업장별 일자별 출근 인원 364건(합성·가명)이고, 두 사업을 같은 모델로 저장해 비교할 수 있습니다." |
| 데이터 요약 | "`/api/data/summary` 가 기간·건수·평균/최대/최소와 최근 30일 대 이전 평균 추세를 계산합니다." |
| Firestore | "`db.py` 한 파일만 Firestore 를 만지고, 키가 없거나 틀리면 메모리 모드로 자동 전환돼 로컬에서 바로 학습할 수 있습니다." |
| 대화 기록 | "목록은 messages 없이 가볍게, 상세 조회에서 messages 전체를 돌려주는 (A) 방식입니다." |
| 컨텍스트 주입 | "요약을 글로 바꿔 지침 기준값·체크리스트와 함께 시스템 프롬프트에 넣고, '프롬프트 보기'로 그대로 보여 줍니다." |
| /api/chat 흐름 | "요약 조회 → 프롬프트 삽입 → GPT 호출 → 대화 자동 저장 순서로 한 요청 안에서 처리합니다." |
| 원칙·안전장치 | "AI는 설명만 하고 날짜·금액은 규칙엔진이 계산하며, ⚠ 미확인 수치에는 '지침 원문 확인 필요'를 서버가 보장합니다." |
| Function Calling | "개별 기록·사업 비교·일정 계산이 필요할 때만 도구를 부르고, 무엇을 불렀는지 답변 아래에 표시합니다." |
| 비용 통제 | "gpt-4o-mini, 700토큰, 최근 10개 메시지, 도구 2라운드로 묶었고 키가 없으면 호출 자체를 하지 않습니다." |
| CORS·환경 변수 | "프론트 주소를 `ALLOWED_ORIGINS` 에 넣어야 브라우저가 허용하고, 모든 키는 환경 변수라 코드·깃에 없습니다." |
| 프론트 4화면 | "채팅(로딩 표시)·데이터 관리·대화 기록·데이터 요약을 한 화면에 Vanilla JS 로 만들었습니다." |
| 배포 | "백엔드는 Render, 프론트는 Vercel 이고, 같은 백엔드를 Vercel 에도 올려 `?api=` 로 번갈아 비교합니다." |
| 콜드스타트 대응 | "Render 무료 티어가 잠들어 3초 넘게 걸리면 '첫 응답 30초' 안내를 띄웁니다." |
| 보너스 | "도구 호출, statistics, 그래프, CSV, 다크 모드를 모두 구현했습니다." |
