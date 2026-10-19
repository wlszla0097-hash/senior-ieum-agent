// build.js — Vercel 빌드 단계: 정적 파일을 dist/ 로 복사하고 config.js 의 DEFAULT_API 줄만 환경 변수 API_BASE_URL 값으로 바꾼다.
// Vercel 설정(frontend/vercel.json): Root Directory=frontend, Build Command=node build.js, Output Directory=dist
// 로컬 확인: node build.js  (API_BASE_URL 이 없으면 localhost:8000 그대로)
const fs = require("fs");
const path = require("path");

const src = __dirname;
const out = path.join(src, "dist");
const STATIC = ["index.html", "style.css", "app.js"];

fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out);
for (const f of STATIC) fs.copyFileSync(path.join(src, f), path.join(out, f));

const api = (process.env.API_BASE_URL || "http://localhost:8000").trim().replace(/\/+$/, "");
if (!/^https?:\/\//.test(api)) {
  console.error(`API_BASE_URL 은 http:// 또는 https:// 로 시작해야 합니다: ${api}`);
  process.exit(1);
}
const config = fs.readFileSync(path.join(src, "config.js"), "utf8");
const pattern = /const DEFAULT_API = "[^"]*";/;
if (!pattern.test(config)) {
  console.error("config.js 에서 DEFAULT_API 줄을 찾지 못했습니다");
  process.exit(1);
}
fs.writeFileSync(path.join(out, "config.js"), config.replace(pattern, `const DEFAULT_API = ${JSON.stringify(api)};`));
console.log(`built → dist/ (${STATIC.length + 1} files, API_BASE_URL = ${api})`);
