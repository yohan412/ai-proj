# 데이터베이스

이 프로젝트는 SQLite 파일 데이터베이스를 사용합니다. Oracle이나 Docker DB는 필요하지 않습니다.

## 파일 위치

Spring Boot를 `CL-Project`에서 실행하면 다음 파일이 생성됩니다.

```text
CL-Project/data/aikademia.db
```

접속 정보는 `src/main/resources/application.properties`에 있습니다.

```properties
spring.datasource.url=jdbc:sqlite:./data/aikademia.db
spring.jpa.hibernate.ddl-auto=update
```

`ddl-auto=update`라서 엔티티 기준으로 테이블을 만들고, 없는 컬럼을 추가합니다. 기본 키는 자동 증가입니다.

## 테이블

- `USERS` 회원
- `VIDEOS` 영상
- `VIDEO_CHAPTERS` 챕터
- `USER_ATTENTION_LOGS` 집중도 기록
- `CHAPTER_ATTENTION_AVG` 챕터 평균 집중도

데이터베이스 파일을 지우면 다음 실행 때 빈 데이터베이스가 다시 만들어집니다.
