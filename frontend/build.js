
const fs = require("node:fs");

const apiBaseUrl = (
  process.env.API_BASE_URL || "http://127.0.0.1:8000"
).trim().replace(/\/+$/, "");

if (!/^https?:\/\/[a-zA-Z0-9.-]+(?::\d+)?$/.test(apiBaseUrl)) {
  throw new Error("API_BASE_URL은 유효한 HTTP(S) 서버 URL이어야 합니다.");
}

fs.writeFileSync(
  "config.js",
  `window.MYDATA_API_BASE_URL = ${JSON.stringify(apiBaseUrl)};\n`,
  "utf8"
);

console.log("Frontend API URL configured.");
