// config.js — 백엔드 주소를 정하는 단 한 곳 (우선순위: 주소창 ?api= → 브라우저에 기억된 값 → DEFAULT_API).
// DEFAULT_API: 로컬은 localhost:8000. Vercel 배포 때는 build.js 가 환경 변수 API_BASE_URL 값으로 이 줄을 바꿔 dist/ 에 쓴다.
// ?api=https://…  → 그 백엔드를 기억해 사용 (Render ↔ Vercel 백엔드 번갈아 테스트) / ?api=reset → 기억 지우고 기본값으로.
(function () {
  const DEFAULT_API = "http://localhost:8000"; // build.js 가 교체하는 줄
  let stored = null;
  try {
    const q = new URLSearchParams(location.search).get("api");
    if (q === "reset") localStorage.removeItem("API_BASE_URL");
    else if (q && /^https?:\/\//.test(q)) localStorage.setItem("API_BASE_URL", q.replace(/\/+$/, ""));
    stored = localStorage.getItem("API_BASE_URL");
  } catch (e) { /* 저장소가 막힌 브라우저에서는 기본값만 사용 */ }
  window.API_BASE_URL = stored || DEFAULT_API;
  window.API_SOURCE = stored ? "?api= 로 지정" : "기본값";
})();
