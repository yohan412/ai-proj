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
    USER_TYPE       VARCHAR2(20)    DEFAULT 'student' NOT NULL,
    ENABLED         NUMBER(1)       DEFAULT 1 NOT NULL,
    CREATED_AT      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UPDATED_AT      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- 제약 조건
    CONSTRAINT PK_USERS PRIMARY KEY (USER_ID),
    CONSTRAINT UK_USERNAME UNIQUE (USERNAME),
    CONSTRAINT UK_EMAIL UNIQUE (EMAIL),
    CONSTRAINT CK_ENABLED CHECK (ENABLED IN (0, 1)),
    CONSTRAINT CK_USER_TYPE CHECK (USER_TYPE IN ('admin', 'teacher', 'student'))
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
COMMENT ON COLUMN USERS.USER_TYPE IS '사용자 유형 (admin, teacher, student)';
COMMENT ON COLUMN USERS.ENABLED IS '계정 활성화 여부 (1: 활성, 0: 비활성)';
COMMENT ON COLUMN USERS.CREATED_AT IS '생성일시';
COMMENT ON COLUMN USERS.UPDATED_AT IS '수정일시';

-- =========================================
-- 샘플 데이터
-- =========================================
-- 관리자 계정 (비밀번호: admin123)
-- BCrypt 해시: $2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy
INSERT INTO USERS (USER_ID, NAME, EMAIL, ORGANIZATION, USERNAME, PASSWORD, USER_TYPE, ENABLED, CREATED_AT, UPDATED_AT)
VALUES (
    USER_SEQ.NEXTVAL,
    '관리자',
    'admin@aikademia.com',
    'AIkademia',
    'admin',
    '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy',
    'admin',
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

COMMIT;

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
    CONSTRAINT PK_VIDEO_CHAPTERS PRIMARY KEY (CHAPTER_ID),
    CONSTRAINT FK_VC_STORED_NAME FOREIGN KEY (STORED_NAME) REFERENCES VIDEOS(STORED_NAME) ON DELETE CASCADE
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
-- 시선 추적 집중도 테이블 스키마
-- =========================================

-- 기존 시퀀스 삭제 (있는 경우)
DROP SEQUENCE ATTENTION_LOG_SEQ;
DROP SEQUENCE ATTENTION_AVG_SEQ;

-- 기존 테이블 삭제 (있는 경우)
DROP TABLE CHAPTER_ATTENTION_AVG CASCADE CONSTRAINTS;
DROP TABLE USER_ATTENTION_LOGS CASCADE CONSTRAINTS;

-- =========================================
-- 집중도 로그 시퀀스 생성
-- =========================================
CREATE SEQUENCE ATTENTION_LOG_SEQ
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;

-- =========================================
-- 평균 집중도 시퀀스 생성
-- =========================================
CREATE SEQUENCE ATTENTION_AVG_SEQ
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;

-- =========================================
-- 유저별 챕터 집중도 로그 테이블
-- =========================================
CREATE TABLE USER_ATTENTION_LOGS (
    LOG_ID              NUMBER(19)      NOT NULL,
    USER_ID             NUMBER(19)      NOT NULL,
    CHAPTER_ID          NUMBER(19)      NOT NULL,
    ATTENTION_SCORE     NUMBER(4,3)     NOT NULL,
    CREATED_AT          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    UPDATED_AT          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- 제약 조건
    CONSTRAINT PK_USER_ATTENTION_LOGS PRIMARY KEY (LOG_ID),
    CONSTRAINT FK_UAL_USER FOREIGN KEY (USER_ID) REFERENCES USERS(USER_ID) ON DELETE CASCADE,
    CONSTRAINT FK_UAL_CHAPTER FOREIGN KEY (CHAPTER_ID) REFERENCES VIDEO_CHAPTERS(CHAPTER_ID) ON DELETE CASCADE,
    CONSTRAINT UK_UAL_USER_CHAPTER UNIQUE (USER_ID, CHAPTER_ID),
    CONSTRAINT CHK_UAL_SCORE CHECK (ATTENTION_SCORE >= 0 AND ATTENTION_SCORE <= 1)
);

-- =========================================
-- 챕터별 평균 집중도 테이블
-- =========================================
CREATE TABLE CHAPTER_ATTENTION_AVG (
    AVG_ID              NUMBER(19)      NOT NULL,
    CHAPTER_ID          NUMBER(19)      NOT NULL,
    AVG_ATTENTION_SCORE NUMBER(4,3)     NOT NULL,
    TOTAL_VIEWS         NUMBER(10)      DEFAULT 0 NOT NULL,
    UPDATED_AT          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- 제약 조건
    CONSTRAINT PK_CHAPTER_ATTENTION_AVG PRIMARY KEY (AVG_ID),
    CONSTRAINT FK_CAA_CHAPTER FOREIGN KEY (CHAPTER_ID) REFERENCES VIDEO_CHAPTERS(CHAPTER_ID) ON DELETE CASCADE,
    CONSTRAINT UK_CAA_CHAPTER UNIQUE (CHAPTER_ID),
    CONSTRAINT CHK_CAA_SCORE CHECK (AVG_ATTENTION_SCORE >= 0 AND AVG_ATTENTION_SCORE <= 1)
);

-- =========================================
-- 인덱스 생성 (성능 최적화)
-- =========================================
CREATE INDEX IDX_UAL_USER_ID ON USER_ATTENTION_LOGS(USER_ID);
CREATE INDEX IDX_UAL_CHAPTER_ID ON USER_ATTENTION_LOGS(CHAPTER_ID);
CREATE INDEX IDX_CAA_CHAPTER_ID ON CHAPTER_ATTENTION_AVG(CHAPTER_ID);

-- =========================================
-- 테이블 코멘트
-- =========================================
COMMENT ON TABLE USER_ATTENTION_LOGS IS '사용자별 챕터 시청 집중도 로그';
COMMENT ON COLUMN USER_ATTENTION_LOGS.LOG_ID IS '로그 순번 (Primary Key)';
COMMENT ON COLUMN USER_ATTENTION_LOGS.USER_ID IS '사용자 ID (FK)';
COMMENT ON COLUMN USER_ATTENTION_LOGS.CHAPTER_ID IS '챕터 ID (FK)';
COMMENT ON COLUMN USER_ATTENTION_LOGS.ATTENTION_SCORE IS '집중도 점수 (0.000 ~ 1.000)';
COMMENT ON COLUMN USER_ATTENTION_LOGS.CREATED_AT IS '최초 기록일시';
COMMENT ON COLUMN USER_ATTENTION_LOGS.UPDATED_AT IS '최종 수정일시';

COMMENT ON TABLE CHAPTER_ATTENTION_AVG IS '챕터별 평균 집중도 통계';
COMMENT ON COLUMN CHAPTER_ATTENTION_AVG.AVG_ID IS '평균 통계 순번 (Primary Key)';
COMMENT ON COLUMN CHAPTER_ATTENTION_AVG.CHAPTER_ID IS '챕터 ID (FK)';
COMMENT ON COLUMN CHAPTER_ATTENTION_AVG.AVG_ATTENTION_SCORE IS '평균 집중도 점수';
COMMENT ON COLUMN CHAPTER_ATTENTION_AVG.TOTAL_VIEWS IS '총 시청 횟수';
COMMENT ON COLUMN CHAPTER_ATTENTION_AVG.UPDATED_AT IS '최종 업데이트일시';

-- =========================================
-- 스키마 생성 완료
-- =========================================

