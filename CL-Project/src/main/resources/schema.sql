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
-- 스키마 생성 완료
-- =========================================

