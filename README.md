
# MyData AI — 운동 기록 분석 비서

운동 기록을 저장하고 시계열 통계를 분석한 뒤, GPT가 실제 데이터를 바탕으로 맞춤형 답변을 제공하는 웹 애플리케이션입니다.

## 주요 기능

- 운동 기록 생성, 조회, 수정, 삭제
- 기간, 운동 시간 합계·평균·최대·최소, 소모 칼로리 요약
- 최근 7일과 이전 7일 운동량 비교
- 데이터 요약을 시스템 프롬프트에 주입하는 AI 채팅
- Firestore에 대화 자동 저장
- 대화 목록 조회, 특정 대화 불러오기, 삭제
- Swagger UI 및 반응형 웹 화면

## 기술 스택

- Python 3.10+
- FastAPI, Uvicorn, Pydantic
- Firebase Admin SDK, Cloud Firestore
- OpenAI Python SDK
- HTML, CSS, Vanilla JavaScript
- Render (백엔드), Vercel (프론트엔드)

## 배포 주소

배포를 완료한 후 아래 값을 실제 주소로 바꾸세요.

- Frontend: https://YOUR-FRONTEND.vercel.app
- Backend API: https://YOUR-BACKEND.onrender.com
- Swagger UI: https://YOUR-BACKEND.onrender.com/docs
- Health: https://YOUR-BACKEND.onrender.com/health

## 사전 준비

1. Python 3.10 이상 설치
2. Firebase 프로젝트 및 Firestore Database 생성
3. Firebase 서비스 계정 키 발급
4. OpenAI API 키 발급 및 API 사용 권한 확인
5. GitHub, Render, Vercel 계정 준비

## 로컬 실행

### 1. 백엔드

저장소 루트에서 실행합니다.

```bash
cd backend
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

패키지 설치:

```bash
pip install -r requirements.txt
```

`.env.example`을 `.env`로 복사하고 키와 Firebase 설정을 입력합니다.

Windows:

```powershell
Copy-Item .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

백엔드 실행:

```bash
uvicorn main:app --reload
```

확인 주소:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

### 2. 테스트 데이터 생성

별도 터미널에서 가상환경을 활성화하고 실행합니다.

```bash
cd backend
python seed.py
```

Firestore에 가상의 운동 기록이 생성됩니다. 테스트 Firebase 프로젝트에서 한 번만 실행하는 것을 권장합니다.

### 3. 프론트엔드

새 터미널에서 실행합니다.

```bash
cd frontend
python -m http.server 5500
```

브라우저에서 http://127.0.0.1:5500 을 엽니다.

기본 API 주소는 http://127.0.0.1:8000 입니다.

## 환경 변수

### 백엔드

| 변수 | 설명 |
|---|---|
| OPENAI_API_KEY | OpenAI 비밀 API 키 |
| OPENAI_MODEL | 사용할 모델명 |
| FIREBASE_SERVICE_ACCOUNT_JSON | 서비스 계정 JSON 문자열 |
| FIREBASE_SERVICE_ACCOUNT_PATH | 서비스 계정 JSON 파일 경로 대안 |
| FIREBASE_PROJECT_ID | Firebase 프로젝트 ID |
| ALLOWED_ORIGINS | 허용할 프론트엔드 origin 목록 |
| MAX_CHAT_HISTORY | GPT에 전달할 과거 메시지 수 |
| MAX_OUTPUT_TOKENS | 답변 생성 토큰 제한 |

JSON 문자열 방식과 파일 경로 방식 중 하나만 설정하면 됩니다.

### 프론트엔드 (Vercel)

| 변수 | 설명 |
|---|---|
| API_BASE_URL | Render 백엔드의 공개 HTTPS URL |

Vercel 프로젝트 Settings → Environment Variables에서 설정합니다.
이 값은 빌드 과정에서 정적 JavaScript 설정으로 생성되므로 비밀 키를 넣지 마세요.

## 배포

### Render

1. GitHub 저장소를 Render에 연결합니다.
2. `backend/render.yaml` 설정으로 Web Service를 생성합니다.
3. `OPENAI_API_KEY`를 등록합니다.
4. Firebase 서비스 계정 JSON을 한 줄 JSON 문자열로 등록합니다.
5. `FIREBASE_PROJECT_ID`를 등록합니다.
6. `ALLOWED_ORIGINS`에 Vercel 프론트엔드 주소를 등록합니다.
7. 배포 후 `/health`와 `/docs`를 확인합니다.

### Vercel

1. GitHub 저장소를 Vercel에 연결합니다.
2. Root Directory를 `frontend`로 설정합니다.
3. Build Command를 `npm run build`로 설정합니다.
4. Output Directory를 `.`로 설정합니다.
5. `API_BASE_URL`에 Render 백엔드 URL을 설정합니다.
6. 재배포 후 프론트엔드에서 CRUD 및 채팅을 테스트합니다.

## 데이터 분석 방식

- 전체 운동 시간: 모든 기록의 운동 시간 합계
- 평균·최대·최소: 기록별 운동 시간 통계
- 총 소모 칼로리: 저장된 칼로리의 합계
- 운동한 날짜: 기록이 존재하는 고유 날짜 개수
- 전체 추세: 최근 최대 7개 기록의 평균과 그 이전 최대 7개 기록의 평균 비교
- 주간 비교: 오늘을 포함한 최근 7일과 그 직전 7일의 운동 시간 합계 비교

## 테스트 체크리스트

- [ ] Swagger에서 운동 기록 POST 성공
- [ ] GET 목록에 생성된 기록 표시
- [ ] PUT으로 기록 수정
- [ ] DELETE로 기록 삭제
- [ ] 요약 API의 통계 값 확인
- [ ] 채팅 질문에 데이터 기반 답변 반환
- [ ] 대화 자동 저장 및 목록 조회
- [ ] 저장된 대화 불러오기 및 삭제
- [ ] 브라우저 화면에서 기록 CRUD 확인
- [ ] Render와 Vercel 배포 환경에서 API 연결 확인
- [ ] 잘못된 입력값에 422 반환 확인

## 제출 스크린샷

1. 데이터 요약과 AI 질문·답변이 함께 보이는 채팅 화면
2. 운동 기록 추가 또는 수정·삭제가 보이는 데이터 관리 화면
3. 이전 대화를 선택해 메시지를 불러온 대화 기록 화면

## 보안 및 비용

- `.env`와 서비스 계정 키는 Git에 커밋하지 않습니다.
- 브라우저 코드에 OpenAI 키 또는 Firebase 서비스 계정 키를 넣지 않습니다.
- OpenAI 호출은 토큰 제한을 적용하지만 실제 API 과금이 발생할 수 있습니다.
- 이 버전은 사용자 인증을 구현하지 않은 개인 프로젝트용입니다.
  여러 사용자가 사용하는 서비스로 공개하기 전에 인증, 사용자별 데이터 접근 제어,
  요청 제한 등을 추가해야 합니다.
- Render 무료 서비스는 첫 요청이 지연될 수 있습니다.
