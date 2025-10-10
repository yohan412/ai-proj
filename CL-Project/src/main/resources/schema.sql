-- =========================================
-- AIkademia 사용자 테이블 스키마
-- Oracle Database 용
-- =========================================

-- 기존 시퀀스 삭제 (있는 경우)
DROP SEQUENCE USER_SEQ;

-- 기존 테이블 삭제 (있는 경우)
DROP TABLE USERS CASCADE CONSTRAINTS;

-- =========================================
-- 사용자 시퀀스 생성 (PK 자동 증가용)
-- =========================================
CREATE SEQUENCE USER_SEQ
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;

-- =========================================
-- 사용자 테이블 생성
-- =========================================
CREATE TABLE USERS (
    USER_ID         NUMBER(19)      NOT NULL,
    NAME            VARCHAR2(100)   NOT NULL,
    EMAIL           VARCHAR2(200)   NOT NULL,
    ORGANIZATION    VARCHAR2(200)   NOT NULL,
    USERNAME        VARCHAR2(50)    NOT NULL,
    PASSWORD        VARCHAR2(255)   NOT NULL,
    ENABLED         NUMBER(1)       DEFAULT 1 NOT NULL,
    CREATED_AT      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UPDATED_AT      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- 제약 조건
    CONSTRAINT PK_USERS PRIMARY KEY (USER_ID),
    CONSTRAINT UK_USERNAME UNIQUE (USERNAME),
    CONSTRAINT UK_EMAIL UNIQUE (EMAIL),
    CONSTRAINT CK_ENABLED CHECK (ENABLED IN (0, 1))
);

-- =========================================
-- 인덱스 생성 (성능 최적화)
-- =========================================
CREATE INDEX IDX_USERNAME ON USERS(USERNAME);
CREATE INDEX IDX_EMAIL ON USERS(EMAIL);
CREATE INDEX IDX_CREATED_AT ON USERS(CREATED_AT);

-- =========================================
-- 테이블 코멘트
-- =========================================
COMMENT ON TABLE USERS IS '사용자 정보 테이블';
COMMENT ON COLUMN USERS.USER_ID IS '사용자 순번 (Primary Key, 자동 증가)';
COMMENT ON COLUMN USERS.NAME IS '사용자 이름';
COMMENT ON COLUMN USERS.EMAIL IS '이메일 주소 (고유값)';
COMMENT ON COLUMN USERS.ORGANIZATION IS '소속';
COMMENT ON COLUMN USERS.USERNAME IS '로그인 아이디 (고유값)';
COMMENT ON COLUMN USERS.PASSWORD IS '비밀번호 (BCrypt 암호화)';
COMMENT ON COLUMN USERS.ENABLED IS '계정 활성화 여부 (1: 활성, 0: 비활성)';
COMMENT ON COLUMN USERS.CREATED_AT IS '생성일시';
COMMENT ON COLUMN USERS.UPDATED_AT IS '수정일시';

-- =========================================
-- 샘플 데이터 (선택사항)
-- =========================================
-- 테스트용 사용자 (비밀번호: password123)
-- BCrypt 해시: $2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy
/*
INSERT INTO USERS (USER_ID, NAME, EMAIL, ORGANIZATION, USERNAME, PASSWORD, ENABLED, CREATED_AT, UPDATED_AT)
VALUES (
    USER_SEQ.NEXTVAL,
    '테스트 사용자',
    'test@example.com',
    '테스트 소속',
    'testuser',
    '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy',
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

COMMIT;
*/

-- =========================================
-- 영상 관리 테이블 스키마
-- =========================================

-- 기존 시퀀스 삭제 (있는 경우)
DROP SEQUENCE VIDEO_SEQ;
DROP SEQUENCE CHAPTER_SEQ;

-- 기존 테이블 삭제 (있는 경우)
DROP TABLE VIDEO_CHAPTERS CASCADE CONSTRAINTS;
DROP TABLE VIDEOS CASCADE CONSTRAINTS;

-- =========================================
-- 영상 시퀀스 생성 (PK 자동 증가용)
-- =========================================
CREATE SEQUENCE VIDEO_SEQ
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;

-- =========================================
-- 챕터 시퀀스 생성 (PK 자동 증가용)
-- =========================================
CREATE SEQUENCE CHAPTER_SEQ
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;

-- =========================================
-- 영상 테이블 생성
-- =========================================
CREATE TABLE VIDEOS (
    VIDEO_ID        NUMBER(19)      NOT NULL,
    STORED_NAME     VARCHAR2(500)   NOT NULL,
    USER_NAME       VARCHAR2(200)   NOT NULL,
    FILE_PATH       VARCHAR2(1000)  NOT NULL,
    DURATION        NUMBER(10,2)    DEFAULT 0 NOT NULL,
    SEGMENTS        CLOB,
    DETECTED_LANG   VARCHAR2(10),
    CREATED_AT      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UPDATED_AT      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- 제약 조건
    CONSTRAINT PK_VIDEOS PRIMARY KEY (VIDEO_ID),
    CONSTRAINT UK_STORED_NAME UNIQUE (STORED_NAME)
);

-- =========================================
-- 영상 구간(챕터) 테이블 생성
-- =========================================
CREATE TABLE VIDEO_CHAPTERS (
    CHAPTER_ID      NUMBER(19)      NOT NULL,
    STORED_NAME     VARCHAR2(500)   NOT NULL,
    START_TIME      NUMBER(10,2)    NOT NULL,
    END_TIME        NUMBER(10,2)    NOT NULL,
    TITLE           VARCHAR2(500)   NOT NULL,
    SUMMARY         VARCHAR2(2000),
    CREATED_AT      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UPDATED_AT      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- 제약 조건
    CONSTRAINT PK_VIDEO_CHAPTERS PRIMARY KEY (CHAPTER_ID)
);

-- =========================================
-- 인덱스 생성 (성능 최적화)
-- =========================================
CREATE INDEX IDX_VIDEO_STORED_NAME ON VIDEOS(STORED_NAME);
CREATE INDEX IDX_VIDEO_USER_NAME ON VIDEOS(USER_NAME);
CREATE INDEX IDX_VIDEO_CREATED_AT ON VIDEOS(CREATED_AT);
CREATE INDEX IDX_CHAPTER_STORED_NAME ON VIDEO_CHAPTERS(STORED_NAME);
CREATE INDEX IDX_CHAPTER_START_TIME ON VIDEO_CHAPTERS(START_TIME);

-- =========================================
-- 테이블 코멘트
-- =========================================
COMMENT ON TABLE VIDEOS IS '영상 정보 테이블';
COMMENT ON COLUMN VIDEOS.VIDEO_ID IS '영상 순번 (Primary Key, 자동 증가)';
COMMENT ON COLUMN VIDEOS.STORED_NAME IS '실제 저장된 파일명 (고유값)';
COMMENT ON COLUMN VIDEOS.USER_NAME IS '사용자가 저장한 이름';
COMMENT ON COLUMN VIDEOS.FILE_PATH IS '파일 저장 경로';
COMMENT ON COLUMN VIDEOS.DURATION IS '영상 길이(초)';
COMMENT ON COLUMN VIDEOS.SEGMENTS IS '자막 세그먼트 (JSON 형식)';
COMMENT ON COLUMN VIDEOS.DETECTED_LANG IS '감지된 언어 코드 (ko, en, ja 등)';
COMMENT ON COLUMN VIDEOS.CREATED_AT IS '등록일시';
COMMENT ON COLUMN VIDEOS.UPDATED_AT IS '수정일시';

COMMENT ON TABLE VIDEO_CHAPTERS IS '영상 구간(챕터) 정보 테이블';
COMMENT ON COLUMN VIDEO_CHAPTERS.CHAPTER_ID IS '구간 순번 (Primary Key, 자동 증가)';
COMMENT ON COLUMN VIDEO_CHAPTERS.STORED_NAME IS '영상 파일명 (참조용)';
COMMENT ON COLUMN VIDEO_CHAPTERS.START_TIME IS '구간 시작 시점(초)';
COMMENT ON COLUMN VIDEO_CHAPTERS.END_TIME IS '구간 종료 시점(초)';
COMMENT ON COLUMN VIDEO_CHAPTERS.TITLE IS '구간 주제(제목)';
COMMENT ON COLUMN VIDEO_CHAPTERS.SUMMARY IS '구간 요약';
COMMENT ON COLUMN VIDEO_CHAPTERS.CREATED_AT IS '등록일시';
COMMENT ON COLUMN VIDEO_CHAPTERS.UPDATED_AT IS '수정일시';

-- =========================================
-- 스키마 생성 완료
-- =========================================

