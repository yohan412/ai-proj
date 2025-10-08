# 데이터베이스 설정 가이드

## 📋 목차
1. [Oracle Database 설정](#oracle-database-설정)
2. [테이블 생성](#테이블-생성)
3. [Spring Boot 설정](#spring-boot-설정)
4. [회원가입 테스트](#회원가입-테스트)

---

## 🗄️ Oracle Database 설정

### 1. Oracle Database 설치 확인
- Oracle Database 11g 이상 필요
- Oracle XE (Express Edition) 권장

### 2. 데이터베이스 접속 정보 확인
```
호스트: localhost
포트: 1521
SID: XE (또는 ORCL)
사용자명: your_username
비밀번호: your_password
```

### 3. SQL Developer로 접속
1. VS Code의 SQL Developer 확장 또는 Oracle SQL Developer 사용
2. 위 정보로 연결 테스트

---

## 📊 테이블 생성

### Option 1: SQL 스크립트 직접 실행 (권장)

`src/main/resources/schema.sql` 파일을 Oracle에서 실행:

```sql
-- SQL Developer에서 실행
@schema.sql
```

또는 파일 내용을 복사하여 실행

### Option 2: Hibernate 자동 생성 (개발용)

`application.properties`에서 이미 설정됨:
```properties
spring.jpa.hibernate.ddl-auto=update
```

Spring Boot 실행 시 자동으로 테이블 생성됨

---

## ⚙️ Spring Boot 설정

### 1. `application.properties` 수정

파일 위치: `src/main/resources/application.properties`

```properties
# Oracle 접속 정보 수정 (17-20번 줄)
spring.datasource.url=jdbc:oracle:thin:@localhost:1521:XE
spring.datasource.username=your_username  # ← 실제 사용자명으로 변경
spring.datasource.password=your_password  # ← 실제 비밀번호로 변경
```

### 2. Oracle 연결 테스트

```bash
# Spring Boot 실행
cd CL-Project
.\mvnw.cmd clean package -DskipTests
cd ..
java -jar CL-Project\target\CL-Project-0.0.1-SNAPSHOT.jar
```

콘솔에서 다음 메시지 확인:
```
HikariPool-1 - Start completed.
Hibernate: ...
```

---

## 🧪 회원가입 테스트

### 1. 브라우저에서 접속
```
http://localhost:8181/
```

### 2. 회원가입 버튼 클릭
우측 상단 "Sign Up" 클릭

### 3. 정보 입력
- **이름**: 홍길동
- **이메일**: hong@example.com
- **소속**: AI 연구소
- **아이디**: hong123 (최소 4자)
- **비밀번호**: password123 (최소 8자)
- **비밀번호 확인**: password123

### 4. 가입하기 클릭

### 5. 성공 확인
- 알림: "회원가입이 완료되었습니다!"
- 자동으로 로그인 팝업 열림

### 6. 데이터베이스 확인

SQL Developer에서 확인:
```sql
SELECT * FROM USERS;
```

확인 사항:
- ✅ USER_ID가 자동으로 증가 (1, 2, 3...)
- ✅ PASSWORD가 암호화되어 저장 ($2a$10$...)
- ✅ CREATED_AT, UPDATED_AT이 자동으로 설정됨

---

## 🔒 보안 기능

### 비밀번호 암호화
- **알고리즘**: BCrypt
- **저장 형식**: `$2a$10$...` (60자)
- **특징**: 
  - 단방향 암호화 (복호화 불가능)
  - Salt 자동 생성
  - 같은 비밀번호도 매번 다른 해시 생성

### 중복 확인
- **아이디**: UNIQUE 제약 + 서버 검증
- **이메일**: UNIQUE 제약 + 서버 검증

---

## 🐛 문제 해결

### 문제 1: Oracle 연결 실패
```
Error: Cannot create PoolableConnectionFactory
```

**해결책:**
1. Oracle 서비스 실행 확인
2. `application.properties`의 접속 정보 확인
3. 방화벽 확인 (포트 1521)

### 문제 2: 테이블이 생성되지 않음
```
Table or view does not exist
```

**해결책:**
1. `schema.sql` 수동 실행
2. `spring.jpa.hibernate.ddl-auto=create` 로 변경 (최초 1회)

### 문제 3: Spring Security로 인해 모든 페이지 접근 불가
```
401 Unauthorized
```

**해결책:**
- `SecurityConfig.java`에서 이미 공개 페이지 설정됨
- 재빌드 필요: `mvnw clean package -DskipTests`

---

## 📚 API 문서

### 회원가입 API
```
POST /api/auth/signup
Content-Type: application/json

Request:
{
  "name": "홍길동",
  "email": "hong@example.com",
  "organization": "AI 연구소",
  "username": "hong123",
  "password": "password123",
  "passwordConfirm": "password123"
}

Response (성공):
{
  "success": true,
  "message": "회원가입이 완료되었습니다.",
  "userId": 1,
  "username": "hong123"
}

Response (실패):
{
  "success": false,
  "message": "이미 사용 중인 아이디입니다."
}
```

### 아이디 중복 확인 API
```
GET /api/auth/check-username?username=hong123

Response:
{
  "available": false,
  "message": "이미 사용 중인 아이디입니다."
}
```

### 이메일 중복 확인 API
```
GET /api/auth/check-email?email=hong@example.com

Response:
{
  "available": false,
  "message": "이미 사용 중인 이메일입니다."
}
```

---

## 🎯 다음 단계

1. ✅ Oracle DB 접속 정보 설정
2. ✅ SQL 스크립트 실행 (선택사항)
3. ✅ Spring Boot 재빌드
4. ✅ 회원가입 테스트
5. ⏳ 로그인 기능 구현 (다음 작업)

---

## 📞 문의사항

문제가 발생하면 콘솔 로그를 확인하세요:
- Spring Boot 로그: 서버 실행 터미널
- 브라우저 콘솔: F12 → Console 탭
- SQL 쿼리: `spring.jpa.show-sql=true`로 확인 가능

