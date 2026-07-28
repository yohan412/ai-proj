# AIkademia (ai-proj)

교육용 영상을 업로드하면 AI가 **자막 추출 → 챕터 분할 → 구간 설명 → RAG 질의응답**까지 수행하는 생성형 AI 학습 플랫폼입니다.  
시선 추적 기반 **집중도(Attention)** 기록으로 학습 상태를 함께 관리합니다.

---

## 아키텍처

```
Browser (Thymeleaf UI)
        │
        ▼
Spring Boot (:8181)  ──JDBC──►  Oracle DB (:1521)
        │
        └──HTTP──►  Flask AI Microservice (:5001)
                      ├─ Whisper (faster-whisper)  자막/세그먼트
                      ├─ Hugging Face LLM          챕터 · 설명
                      ├─ FFmpeg                    구간 클립
                      └─ RAG + Wikipedia Agent     챗봇 Q&A
```

| 구성 요소 | 역할 | 기본 포트 |
|-----------|------|-----------|
| **Spring Boot** (`CL-Project`) | 웹 UI, 인증, 영상/집중도 API, Flask 연동 | `8181` |
| **Python Flask** (`python-microservice`) | 영상 분석·LLM·RAG 마이크로서비스 | `5001` |
| **Oracle Database** | 사용자, 영상, 챕터, 집중도 데이터 | `1521` |

---

## 주요 기능

- **영상 분석**: Whisper로 음성→자막 세그먼트 추출, LLM으로 챕터 자동 생성
- **챕터 설명**: 선택한 구간에 대한 LLM 상세 설명 생성
- **구간 클립**: FFmpeg로 챕터 구간 영상 자르기
- **AI 챗봇**: 자막 기반 RAG + Wikipedia 검색 Agent로 질의응답
- **회원/세션**: Spring Security 기반 회원가입·로그인·로그아웃
- **집중도**: 챕터별 시선 추적 점수 저장 및 평균 조회
- **관리**: 사용자/콘텐츠 관리 페이지 (`/manage`)

---

## 기술 스택

### Backend (Java)
- Java 17+, Spring Boot 3.3.5
- Spring Security, Spring Data JPA, Thymeleaf
- WebClient / RestTemplate → Flask 연동
- Oracle JDBC (`ojdbc11`)

### AI Microservice (Python)
- Flask, faster-whisper, PyTorch (CUDA 11.8)
- Transformers / Hugging Face LLM (기본: 로컬 HF 모델)
- sentence-transformers + FAISS (RAG)
- KoNLPy, Wikipedia API

### Infra / Tools
- Oracle XE (Docker 이미지 또는 로컬 설치)
- FFmpeg (오디오 추출·영상 클립)
- Conda (Python 환경 분리)

---

## 디렉터리 구조

```
ai-proj/
├── README.md
├── CL-Project/                      # Spring Boot 메인 애플리케이션
│   ├── pom.xml
│   ├── README.md                    # 상세 설치·실행 가이드
│   ├── DATABASE_SETUP.md            # DB 설정 가이드
│   ├── src/main/java/.../CL/Project/
│   │   ├── user/                    # 회원가입·로그인
│   │   ├── video/                   # 영상 저장·조회·스트리밍
│   │   ├── content/                 # 분석 API 프록시
│   │   ├── attention/               # 집중도 API
│   │   ├── manage/                  # 관리 페이지
│   │   ├── flask/                   # FlaskClient
│   │   └── security/                # Spring Security
│   ├── src/main/resources/
│   │   ├── application.properties
│   │   ├── templates/               # index, content, manage
│   │   └── static/                  # CSS, JS
│   └── python-microservice/         # Flask AI 서비스
│       ├── app.py
│       ├── config.py
│       ├── requirements.txt
│       ├── .env.example
│       └── services/
│           ├── transcriber.py       # Whisper 전사
│           ├── chapterizer.py       # 챕터 생성
│           ├── explainer.py         # 구간 설명
│           ├── rag_service.py       # FAISS RAG
│           ├── agent_service.py     # 챗봇 Agent
│           └── wikipedia_tool.py
└── AudioModel/                      # (선택) ffmpeg.exe 등
```

---

## 사전 요구사항

1. **Git**
2. **JDK 17+** (프로젝트 `pom.xml` 기준)
3. **Miniconda / Anaconda**
4. **Docker Desktop** (사전 구성 Oracle DB 이미지 사용 시)
5. **FFmpeg** — PATH에 등록하거나 `ai-proj/AudioModel/ffmpeg.exe`에 배치
6. **GPU + CUDA** (권장) — 로컬 LLM·Whisper 가속용

---

## 빠른 시작

자세한 단계는 [`CL-Project/README.md`](CL-Project/README.md)를 참고하세요.

### 1. Oracle DB 실행

```bash
docker run -d --name oracle-db -p 1521:1521 laoi/cl-project-db:v1
```

> 이미지에 테이블·시퀀스·admin 계정이 포함되어 있습니다.  
> 로컬 Oracle을 쓰는 경우 [`CL-Project/DATABASE_SETUP.md`](CL-Project/DATABASE_SETUP.md)를 참고하세요.

`application.properties` 기본 접속 정보:

| 항목 | 값 |
|------|-----|
| URL | `jdbc:oracle:thin:@localhost:1521/XEPDB1` |
| User | `aiproj` |
| Password | `aiproj` |

### 2. Python 환경

```bash
cd CL-Project/python-microservice

conda create -n cl_env python=3.10 -y
conda activate cl_env
pip install -r requirements.txt

# OCR이 필요한 경우 (선택)
conda create -n ocr_env python=3.10 -y
conda activate ocr_env
pip install -r core/craft/requirements.txt
```

`.env.example`을 복사해 `.env`를 만들고 Hugging Face 토큰 등을 설정합니다.

```bash
cp .env.example .env
# HF_TOKEN, HF_MODEL_ID, WHISPER_MODEL 등 수정
```

### 3. 서비스 실행 (순서 중요)

**터미널 1 — Flask**

```bash
cd CL-Project/python-microservice
conda activate cl_env
python app.py
# → http://localhost:5001
```

**터미널 2 — Spring Boot**

```bash
cd CL-Project
# Windows
mvnw.cmd spring-boot:run
# macOS / Linux
./mvnw spring-boot:run
# → http://localhost:8181
```

### 4. 접속 확인

- 웹: [http://localhost:8181](http://localhost:8181)
- Docker DB 기본 관리자: `admin` / `admin123`
- Analyze 페이지에서 영상 업로드로 파이프라인 검증

---

## 주요 API

### Spring Boot (`:8181`)

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/api/auth/signup` | 회원가입 |
| `POST` | `/api/auth/login` | 로그인 |
| `POST` | `/api/auth/logout` | 로그아웃 |
| `GET` | `/api/auth/session` | 세션 확인 |
| `POST` | `/api/videos/save` | 영상·챕터 저장 |
| `GET` | `/api/videos` | 영상 목록 |
| `GET` | `/api/videos/stream/{storedName}` | 영상 스트리밍 |
| `POST` | `/api/...` (AnalyzeController) | Flask 분석/설명/챗 프록시 |
| `POST` | `/api/attention/save` | 챕터 집중도 저장 |
| `GET` | `/api/attention/chapter/{id}/average` | 챕터 평균 집중도 |

### Flask (`:5001`)

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/health` | 헬스체크·모델 설정 확인 |
| `POST` | `/analyze` | Whisper + LLM 챕터 분석 |
| `POST` | `/clip` | FFmpeg 구간 클립 |
| `POST` | `/explain` | 챕터 상세 설명 |
| `POST` | `/chat` | RAG 기반 AI 챗봇 |

Spring → Flask URL은 `application.properties`의 `app.flask.url`로 지정합니다 (기본: `http://localhost:5001`).

---

## 페이지 라우트

| Path | 설명 |
|------|------|
| `/`, `/main` | 랜딩 (AIkademia) |
| `/content` | 영상 분석·학습 콘텐츠 |
| `/manage` | 관리 페이지 |

---

## 분석 파이프라인

1. 사용자가 영상 업로드
2. Spring이 Flask `/analyze`로 전달
3. **Whisper**가 자막 세그먼트 생성
4. **LLM**이 세그먼트를 챕터로 묶고 (10초 미만 챕터 필터링)
5. 필요 시 `/explain`, `/chat`, `/clip`으로 설명·질의·구간 추출
6. 결과·메타데이터를 Oracle에 저장, 브라우저에서 재생·집중도 기록

---

## 관련 문서

- [CL-Project 설치·실행 가이드](CL-Project/README.md)
- [데이터베이스 설정](CL-Project/DATABASE_SETUP.md)
- [인증 플로우](CL-Project/authentication_flow.txt)

---

## 라이선스 / 템플릿

프론트 UI는 [HTML5 UP Spectral](https://html5up.net/spectral) 템플릿을 기반으로 합니다.
