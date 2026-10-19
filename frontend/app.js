// app.js — 화면 동작: (1) 공통 fetch·콜드스타트 안내 (1b) 사업 탭 (2) 채팅 (3) 대화 기록 (4) 요약·그래프 (5) 데이터 CRUD (5b) HR 공통 계산 (6) 다크 모드.
const API = window.API_BASE_URL;
const $ = (id) => document.getElementById(id);
const PROGRAM_NAME = { senior: "시니어", flexwork: "선택근무", hr: "HR 공통" };
let PROGRAMS = [];            // GET /api/programs 결과 (탭·모드·빠른 질문)
const COLD_START_MS = 3000; // 3초 넘게 걸리면 Render 콜드스타트 안내
let currentConversationId = null;

// ---------- (1) 공통 ----------
let slowPending = 0;
async function api(path, opts = {}, { coldHint = true } = {}) {
  // 채팅은 원래 오래 걸리므로(coldHint=false) 안내를 띄우지 않는다
  let timer = null, shown = false;
  if (coldHint) timer = setTimeout(() => { shown = true; slowPending++; $("cold-start").classList.remove("hidden"); }, COLD_START_MS);
  try {
    const res = await fetch(API + path, { headers: { "Content-Type": "application/json" }, ...opts });
    if (res.status === 204) return null;
    const body = res.headers.get("content-type")?.includes("json") ? await res.json() : await res.text();
    if (!res.ok) throw new Error(errorText(res.status, body));
    return body;
  } finally {
    clearTimeout(timer);
    if (shown && --slowPending === 0) $("cold-start").classList.add("hidden");
  }
}
function errorText(status, body) {
  const d = typeof body === "object" ? body.detail ?? body : body;
  if (status === 422 && Array.isArray(d)) return "입력 확인: " + d.map((e) => `${e.loc?.slice(-1)[0]} — ${e.msg}`).join(", ");
  return `(${status}) ` + (typeof d === "string" ? d : JSON.stringify(d));
}
function esc(s) { return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

async function checkServer() {
  const el = $("server-status");
  try {
    const s = await api("/");
    el.textContent = `연결됨 · 저장소 ${s.storage} · AI ${s.ai === "configured" ? "설정됨" : "미설정"}`;
    el.className = "pill ok";
  } catch (e) {
    el.textContent = "백엔드 연결 실패 — 아래 백엔드 주소 확인";
    el.className = "pill bad";
  }
}


// ---------- (1b) 사업 탭: 서버 registry 가 주는 목록으로 탭·모드·빠른 질문을 그린다 ----------
async function loadPrograms() {
  try { PROGRAMS = await api("/api/programs"); }
  catch (e) { $("program-tabs").innerHTML = `<span class="bad-text small-text">사업 목록 실패: ${esc(e.message)}</span>`; return; }
  let saved = null; try { saved = localStorage.getItem("program"); } catch (e) { /* 무시 */ }
  const nav = $("program-tabs"); nav.innerHTML = "";
  for (const p of PROGRAMS) {
    const b = document.createElement("button");
    b.className = "tab"; b.dataset.id = p.id; b.textContent = p.label; b.title = p.label_long;
    b.addEventListener("click", () => selectProgram(p.id));
    nav.appendChild(b);
  }
  selectProgram(PROGRAMS.some((p) => p.id === saved) ? saved : PROGRAMS[0].id, false);
}
function selectProgram(id, resetChat = true) {
  const p = PROGRAMS.find((x) => x.id === id); if (!p) return;
  $("program").value = id;
  try { localStorage.setItem("program", id); } catch (e) { /* 무시 */ }
  document.querySelectorAll("#program-tabs .tab").forEach((t) => t.classList.toggle("active", t.dataset.id === id));
  const mode = $("mode"); const prev = mode.value; mode.innerHTML = "";
  for (const m of p.modes) { const o = document.createElement("option"); o.value = m.id; o.textContent = m.title; mode.appendChild(o); }
  mode.value = p.modes.some((m) => m.id === prev) ? prev : (p.modes.some((m) => m.id === "qa") ? "qa" : p.modes[0].id);
  const q = $("quick"); q.innerHTML = "";
  for (const qq of p.quick_questions) {
    const b = document.createElement("button"); b.className = "chip"; b.textContent = qq.label; b.dataset.q = qq.question;
    b.addEventListener("click", () => sendMessage(qq.question)); q.appendChild(b);
  }
  $("hr-panel").classList.toggle("hidden", id !== "hr");
  if (id === "hr") loadEmployees();
  if (resetChat && currentConversationId) $("new-chat").click();
}

// ---------- (2) 채팅 ----------
function addMessage(role, text, meta) {
  const box = $("messages");
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = esc(text).replace(/\n/g, "<br>") + (meta ? `<div class="meta">${esc(meta)}</div>` : "");
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

async function sendMessage(text) {
  if (!text.trim() || $("send-btn").disabled) return;
  addMessage("user", text);
  $("chat-input").value = "";
  setChatBusy(true);
  const loading = addMessage("assistant loading", "선임자가 답변을 정리하고 있어요…");
  try {
    const r = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, program: $("program").value, mode: $("mode").value, conversation_id: currentConversationId }),
    }, { coldHint: false });
    currentConversationId = r.conversation_id;
    loading.remove();
    const meta = r.tools_used?.length ? "도구 호출: " + r.tools_used.join(", ") : "";
    addMessage(r.ai_configured ? "assistant" : "assistant warn", r.answer, meta);
    loadConversations();
  } catch (e) {
    loading.remove();
    addMessage("assistant error", "오류: " + e.message);
  } finally {
    setChatBusy(false);
    $("chat-input").focus();
  }
}
function setChatBusy(b) {
  $("send-btn").disabled = b;
  document.querySelectorAll(".chip").forEach((c) => (c.disabled = b));
}

$("chat-form").addEventListener("submit", (e) => { e.preventDefault(); sendMessage($("chat-input").value); });
$("new-chat").addEventListener("click", () => {
  currentConversationId = null;
  $("messages").innerHTML = '<div class="msg assistant">새 대화를 시작합니다. 사업·모드를 확인하고 질문해 주세요.</div>';
  document.querySelectorAll(".conv-list li").forEach((li) => li.classList.remove("active"));
});
$("show-prompt").addEventListener("click", async () => {
  try {
    const r = await api(`/api/chat/prompt-preview?program=${$("program").value}&mode=${$("mode").value}`);
    const s = r.settings;
    $("prompt-meta").textContent = `${r.chars}자 · 모델 ${s.model} · max_tokens ${s.max_tokens} · 최근 ${s.history_limit}개 메시지 · 도구 최대 ${s.max_tool_rounds}라운드 · 도구: ${s.tools.join(", ")}`;
    $("prompt-text").textContent = r.system_prompt;
    $("prompt-dialog").showModal();
  } catch (e) { alert("프롬프트 불러오기 실패: " + e.message); }
});

// ---------- (3) 대화 기록 ----------
async function loadConversations() {
  const ul = $("conv-list");
  try {
    const list = await api("/api/conversations");
    ul.innerHTML = list.length ? "" : '<li class="muted">저장된 대화가 없습니다</li>';
    for (const c of list) {
      const li = document.createElement("li");
      li.className = c.id === currentConversationId ? "active" : "";
      li.innerHTML = `<button class="title" title="불러오기">${esc(c.title)}</button><span class="small-text muted">${PROGRAM_NAME[c.program] || ""} · ${c.message_count}개 메시지</span><button class="x" title="삭제" aria-label="대화 삭제">×</button>`;
      li.querySelector(".title").addEventListener("click", () => openConversation(c.id));
      li.querySelector(".x").addEventListener("click", async (ev) => {
        ev.stopPropagation();
        if (!confirm("이 대화를 삭제할까요?")) return;
        try {
          await api(`/api/conversations/${c.id}`, { method: "DELETE" });
          if (currentConversationId === c.id) $("new-chat").click();
          loadConversations();
        } catch (e) { alert("삭제 실패: " + e.message); }
      });
      ul.appendChild(li);
    }
  } catch (e) { ul.innerHTML = `<li class="muted">불러오기 실패: ${esc(e.message)}</li>`; }
}

async function openConversation(id) {
  try {
    const c = await api(`/api/conversations/${id}`); // (A) 방식: 상세 조회로 messages 전체를 받는다
    currentConversationId = id;
    $("program").value = c.program || "senior";
    $("mode").value = c.mode || "qa";
    $("messages").innerHTML = "";
    for (const m of c.messages || []) addMessage(m.role, m.content);
    loadConversations();
  } catch (e) { alert("대화 불러오기 실패: " + e.message); }
}

// ---------- (4) 요약 + 그래프 ----------
async function loadSummary() {
  const el = $("summary");
  try {
    const s = await api("/api/data/summary");
    const bp = s.by_program || {};
    const row = (label, p) => p && p.count
      ? `<div class="sum-row"><b>${label}</b><span>${p.count}건 · 평균 ${p.metrics.average}명 · 최대 ${p.metrics.max}명 · 최소 ${p.metrics.min}명</span><span class="trend">기간 ${esc(p.period)}<br>최근 30일: ${esc(p.trend)}</span></div>`
      : `<div class="sum-row"><b>${label}</b><span class="muted">데이터 없음</span></div>`;
    el.className = "summary";
    el.innerHTML = `<div class="sum-head">전체 ${s.count}건 · ${esc(s.period)}</div>` + row("시니어인턴십", bp.senior) + row("선택근무제", bp.flexwork);
    await drawChart();
  } catch (e) { el.innerHTML = `<span class="muted">요약 실패: ${esc(e.message)}</span>`; }
}

let lastMonths = [];
async function drawChart(refetch = true) {
  if (refetch) lastMonths = (await api("/api/data/statistics")).months;
  const months = lastMonths;
  const c = $("chart"), ctx = c.getContext("2d");
  const W = c.width, H = c.height, padL = 44, padR = 16, padT = 16, padB = 36;
  ctx.clearRect(0, 0, W, H);
  const style = getComputedStyle(document.documentElement);
  const color = (v) => style.getPropertyValue(v).trim();
  ctx.font = "20px sans-serif";
  if (!months.length) { ctx.fillStyle = color("--muted"); ctx.textAlign = "center"; ctx.fillText("데이터가 없습니다", W / 2, H / 2); return; }
  const max = Math.ceil(Math.max(1, ...months.flatMap((m) => [m.senior || 0, m.flexwork || 0])));
  const x = (i) => padL + (months.length === 1 ? (W - padL - padR) / 2 : (i * (W - padL - padR)) / (months.length - 1));
  const y = (v) => H - padB - (v / max) * (H - padT - padB);
  // 눈금선 + y축 값
  ctx.lineWidth = 1; ctx.textAlign = "right"; ctx.textBaseline = "middle";
  for (let k = 0; k <= 4; k++) {
    const v = (max * k) / 4;
    ctx.strokeStyle = color("--border"); ctx.beginPath(); ctx.moveTo(padL, y(v)); ctx.lineTo(W - padR, y(v)); ctx.stroke();
    ctx.fillStyle = color("--muted"); ctx.fillText(v.toFixed(v % 1 ? 1 : 0), padL - 8, y(v));
  }
  ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
  months.forEach((m, i) => ctx.fillText(m.month.slice(2).replace("-", "."), x(i), H - 10));
  const line = (key, col) => {
    ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = 3; ctx.beginPath();
    let started = false;
    months.forEach((m, i) => { if (m[key] == null) return; started ? ctx.lineTo(x(i), y(m[key])) : ctx.moveTo(x(i), y(m[key])); started = true; });
    ctx.stroke();
    months.forEach((m, i) => { if (m[key] != null) { ctx.beginPath(); ctx.arc(x(i), y(m[key]), 5, 0, Math.PI * 2); ctx.fill(); } });
  };
  line("senior", color("--senior"));
  line("flexwork", color("--flex"));
}

// ---------- (5) 데이터 CRUD ----------
async function loadData() {
  const tb = $("data-rows");
  const p = $("filter-program").value;
  try {
    const rows = (await api(`/api/data?limit=30${p ? "&program=" + p : ""}`)).reverse(); // 최근 30건만 표시
    tb.innerHTML = rows.length ? "" : '<tr><td colspan="6" class="muted">데이터가 없습니다. "샘플 넣기"를 눌러 보세요.</td></tr>';
    for (const r of rows) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${esc(r.date)}</td><td>${PROGRAM_NAME[r.program] || esc(r.program)}</td><td>${esc(r.site)}</td>
        <td><input class="inline-val" type="number" min="0" step="1" value="${esc(r.value)}" aria-label="출근 인원 수정"></td>
        <td><input class="inline-memo" type="text" maxlength="300" value="${esc(r.memo)}" title="${esc(r.memo)}" aria-label="메모 수정"></td>
        <td><button class="x" title="삭제" aria-label="기록 삭제">×</button></td>`;
      const save = async (patch) => {                                                     // 수정(PUT)
        try { await api(`/api/data/${r.id}`, { method: "PUT", body: JSON.stringify(patch) }); status(`수정됨: ${r.date} ${r.site}`); loadSummary(); }
        catch (e) { status("수정 실패: " + e.message, true); }
      };
      tr.querySelector(".inline-val").addEventListener("keydown", (ev) => { if (ev.key === "Enter") save({ value: Number(ev.target.value) }); });
      tr.querySelector(".inline-memo").addEventListener("keydown", (ev) => { if (ev.key === "Enter") save({ memo: ev.target.value }); });
      tr.querySelector(".x").addEventListener("click", async () => {                       // 삭제(DELETE)
        if (!confirm(`${r.date} ${r.site} 기록을 삭제할까요?`)) return;
        try { await api(`/api/data/${r.id}`, { method: "DELETE" }); status(`삭제됨: ${r.date} ${r.site}`); loadData(); loadSummary(); }
        catch (e) { status("삭제 실패: " + e.message, true); }
      });
      tb.appendChild(tr);
    }
  } catch (e) { tb.innerHTML = `<tr><td colspan="6" class="muted">불러오기 실패: ${esc(e.message)}</td></tr>`; }
}
function status(msg, bad) { const el = $("data-status"); el.textContent = msg; el.className = "small-text " + (bad ? "bad-text" : "ok-text"); }

$("data-form").addEventListener("submit", async (e) => {                                   // 추가(POST)
  e.preventDefault();
  try {
    await api("/api/data", { method: "POST", body: JSON.stringify({
      date: $("d-date").value, value: Number($("d-value").value), program: $("d-program").value, site: $("d-site").value, memo: $("d-memo").value }) });
    status("추가됨"); $("d-value").value = ""; $("d-memo").value = ""; loadData(); loadSummary();
  } catch (err) { status("추가 실패: " + err.message, true); }
});
$("seed-btn").addEventListener("click", async () => {
  try {
    const r = await api("/api/data/seed", { method: "POST" });
    status(r.inserted ? `샘플 ${r.inserted}건 입력 (저장소: ${r.storage})` : `이미 데이터가 있어 건너뜀 (현재 ${r.total}건)`);
    loadData(); loadSummary(); loadEmployees();
  } catch (e) { status("샘플 입력 실패: " + e.message, true); }
});
$("export-btn").addEventListener("click", () => { location.href = API + "/api/data/export"; }); // 서버가 attachment 로 내려줘 바로 다운로드
$("refresh-summary").addEventListener("click", loadSummary);
$("filter-program").addEventListener("change", loadData);


// ---------- (5b) HR 공통 계산: 직원 → 계약 시급(수정 가능) → 계산 → 결과 카드 ----------
let currentEmployee = null;
function consentOk() { return $("consent").checked; }
function syncCalcButtons() { document.querySelectorAll("#calc-form [data-calc]").forEach((b) => (b.disabled = !consentOk())); }
$("consent").addEventListener("change", () => { try { localStorage.setItem("consent", consentOk() ? "1" : ""); } catch (e) { /* 무시 */ } syncCalcButtons(); });

async function loadEmployees() {
  const sel = $("emp-select");
  try {
    const list = await api("/api/employees");
    sel.innerHTML = '<option value="">직접 입력</option>';
    for (const e of list) { const o = document.createElement("option"); o.value = e.employee_id; o.textContent = `${e.employee_id} ${e.name} (${e.site})`; sel.appendChild(o); }
    if (!list.length) sel.innerHTML += '<option value="" disabled>직원 없음 — 데이터 관리의 "샘플 넣기"</option>';
    if (currentEmployee) { sel.value = currentEmployee.employee_id; showEmployee(currentEmployee); }
  } catch (e) { sel.innerHTML = `<option value="">목록 실패: ${esc(e.message)}</option>`; }
}
function showEmployee(e) {
  currentEmployee = e;
  $("emp-card").classList.toggle("hidden", !e);
  if (!e) { $("c-wage").value = ""; $("c-weekly").value = ""; return; }
  $("emp-name").textContent = `${e.employee_id} ${e.name}`; $("emp-site").textContent = `${e.site} · 계약일 ${e.contract_date}`;
  $("emp-wage").textContent = Number(e.hourly_wage).toLocaleString(); $("emp-hours").textContent = e.weekly_contract_hours;
  $("emp-source").textContent = e.wage_source_label; $("emp-source").className = "tag " + (e.wage_source === "edited" ? "edited" : "");
  const h = e.wage_history || [];
  $("emp-history").innerHTML = h.length
    ? `계약서 원값 ${Number(e.contract_hourly_wage).toLocaleString()}원 → ` + h.map((x) => `${Number(x.after).toLocaleString()}원 (${esc(x.edited_by)}, ${esc(x.reason)}, ${x.edited_at.slice(0, 10)})`).join(" → ")
    : "수정 이력 없음 — 근로계약서 기재값 그대로";
  $("c-wage").value = e.hourly_wage; $("c-weekly").value = e.weekly_contract_hours;
  $("edit-wage-form").classList.add("hidden");
}
$("emp-select").addEventListener("change", async () => {
  const id = $("emp-select").value;
  if (!id) return showEmployee(null);
  try { showEmployee(await api(`/api/employees/${id}`)); } catch (e) { alert(e.message); }
});
$("edit-wage-btn").addEventListener("click", () => { $("edit-wage-form").classList.toggle("hidden"); $("ew-wage").value = currentEmployee?.hourly_wage || ""; });
$("ew-cancel").addEventListener("click", () => $("edit-wage-form").classList.add("hidden"));
$("edit-wage-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  if (!currentEmployee) return;
  try {
    const e = await api(`/api/employees/${currentEmployee.employee_id}/wage`, { method: "PUT",
      body: JSON.stringify({ hourly_wage: Number($("ew-wage").value), reason: $("ew-reason").value.trim(), edited_by: $("ew-by").value.trim() }) });
    showEmployee(e); $("ew-reason").value = ""; loadEmployees();
  } catch (err) { alert("수정 실패: " + err.message); }
});

async function runCalc(kind) {
  if (!consentOk()) return;
  const body = { employee_id: $("emp-select").value || null };
  const wage = Number($("c-wage").value), weekly = Number($("c-weekly").value);
  if (!body.employee_id || (currentEmployee && wage !== Number(currentEmployee.hourly_wage))) body.hourly_wage = wage || undefined;
  if (kind === "overtime") Object.assign(body, { weekly_contract_hours: weekly || undefined, overtime_hours: Number($("c-ot").value) || 0, night_hours: Number($("c-night").value) || 0,
    holiday_hours: Number($("c-hol").value) || 0, holiday_over_8h: Number($("c-hol8").value) || 0, employees_under_5: $("c-under5").checked });
  if (kind === "weekly-holiday") Object.assign(body, { weekly_contract_hours: weekly || undefined });
  const out = $("calc-result"); out.classList.remove("hidden"); out.innerHTML = '<span class="muted">계산 중…</span>';
  try { renderCalc(kind, await api(`/api/labor/${kind}`, { method: "POST", body: JSON.stringify(body) })); }
  catch (e) { out.innerHTML = `<span class="bad-text">${esc(e.message)}</span>`; }
}
function renderCalc(kind, r) {
  const won = (n) => (n == null ? "-" : Number(n).toLocaleString() + "원");
  let head = "";
  if (kind === "overtime") head = `<div class="big">${won(r.total)}</div><div class="small-text">연장 ${won(r.overtime_pay)} · 야간가산 ${won(r.night_extra)} · 휴일 ${won(r.holiday_pay)}${r.inputs.employees_under_5 ? ` · <b>가산 미적용 시 ${won(r.total_if_no_premium)}</b>` : ""}</div>`;
  if (kind === "min-wage") head = `<div class="big">${r.meets ? "최저임금 이상" : "최저임금 미만 ⚠"}</div><div class="small-text">시급 ${won(r.inputs.hourly_wage)} vs ${r.inputs.year}년 최저 ${won(r.min_wage)} (${r.difference >= 0 ? "+" : ""}${Number(r.difference).toLocaleString()}원) · 월 환산(209h) ${won(r.monthly_209h)}</div>`;
  if (kind === "weekly-holiday") head = `<div class="big">${r.eligible ? `주휴 ${r.weekly_holiday_hours}h` : "주휴 미발생"}</div><div class="small-text">${r.weekly_holiday_pay != null ? "주휴수당 " + won(r.weekly_holiday_pay) : "시급을 넣으면 주휴수당도 계산"}</div>`;
  const emp = r.employee;
  const src = `<div><b>시급 출처</b> ${esc(r.wage_source)}${emp ? ` — ${esc(emp.employee_id)} ${esc(emp.name)}` : ""}${emp && emp.wage_history?.length
    ? `<div class="small-text">계약서 원값 ${won(emp.contract_hourly_wage)} → ${emp.wage_history.map((x) => `${won(x.after)} (${esc(x.edited_by)}: ${esc(x.reason)})`).join(" → ")}</div>` : ""}</div>`;
  $("calc-result").innerHTML = `${head}
    <div><b>계산식</b> <code>${esc(r.formula)}</code></div>
    <div><b>근거</b><ul>${r.basis.map((b) => `<li>${esc(b)}</li>`).join("")}</ul></div>
    ${src}
    ${r.warnings.length ? `<div class="warn"><ul>${r.warnings.map((w) => `<li>${esc(w)}</li>`).join("")}</ul></div>` : ""}
    <div class="disclaimer">${esc(r.disclaimer)}</div>`;
}
$("calc-form").addEventListener("submit", (e) => { e.preventDefault(); runCalc("overtime"); });
document.querySelectorAll('#calc-form [data-calc]:not([type="submit"])').forEach((b) => b.addEventListener("click", () => runCalc(b.dataset.calc)));

// ---------- (6) 다크 모드 ----------
function applyTheme(t, save = true) {
  document.documentElement.dataset.theme = t;
  $("theme-toggle").textContent = t === "dark" ? "☀️" : "🌙";
  if (save) { try { localStorage.setItem("theme", t); } catch (e) { /* 무시 */ } }
  if (lastMonths.length) drawChart(false);
}
$("theme-toggle").addEventListener("click", () => applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));

// ---------- 시작 ----------
(async function init() {
  let theme = null;
  try { theme = localStorage.getItem("theme"); } catch (e) { /* 무시 */ }
  applyTheme(theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"), false);
  $("api-url").textContent = `${API} (${window.API_SOURCE})`;
  const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  $("d-date").value = d.toISOString().slice(0, 10); // 로컬(한국) 날짜 기준 오늘
  try { $("consent").checked = localStorage.getItem("consent") === "1"; } catch (e) { /* 무시 */ }
  syncCalcButtons();
  await checkServer();
  loadPrograms(); loadConversations(); loadSummary(); loadData();
})();
