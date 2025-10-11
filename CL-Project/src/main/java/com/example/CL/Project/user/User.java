package com.example.CL.Project.user;

import jakarta.persistence.*;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * 사용자 엔티티
 * Oracle DB의 USERS 테이블과 매핑
 */
@Entity
@Table(name = "USERS")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User {
    
    /**
     * 순번 (Primary Key, 자동 증가)
     * Oracle Sequence 사용
     */
    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "user_seq")
    @SequenceGenerator(name = "user_seq", sequenceName = "USER_SEQ", allocationSize = 1)
    @Column(name = "USER_ID")
    private Long userId;
    
    /**
     * 이름
     */
    @NotBlank(message = "이름은 필수입니다")
    @Size(max = 100, message = "이름은 100자 이하여야 합니다")
    @Column(name = "NAME", nullable = false, length = 100)
    private String name;
    
    /**
     * 이메일
     */
    @NotBlank(message = "이메일은 필수입니다")
    @Email(message = "올바른 이메일 형식이어야 합니다")
    @Size(max = 200, message = "이메일은 200자 이하여야 합니다")
    @Column(name = "EMAIL", nullable = false, unique = true, length = 200)
    private String email;
    
    /**
     * 소속
     */
    @NotBlank(message = "소속은 필수입니다")
    @Size(max = 200, message = "소속은 200자 이하여야 합니다")
    @Column(name = "ORGANIZATION", nullable = false, length = 200)
    private String organization;
    
    /**
     * 아이디 (로그인용)
     */
    @NotBlank(message = "아이디는 필수입니다")
    @Size(min = 4, max = 50, message = "아이디는 4-50자여야 합니다")
    @Column(name = "USERNAME", nullable = false, unique = true, length = 50)
    private String username;
    
    /**
     * 비밀번호 (암호화되어 저장됨)
     * BCrypt 해시 형태로 저장
     */
    @NotBlank(message = "비밀번호는 필수입니다")
    @Column(name = "PASSWORD", nullable = false, length = 255)
    private String password;
    
    /**
     * 사용자 유형 (admin, teacher, student)
     */
    @Column(name = "USER_TYPE", nullable = false, length = 20)
    @Builder.Default
    private String userType = "student";
    
    /**
     * 계정 활성화 여부
     */
    @Column(name = "ENABLED", nullable = false)
    @Builder.Default
    private Boolean enabled = true;
    
    /**
     * 생성일시
     */
    @Column(name = "CREATED_AT", nullable = false, updatable = false)
    private LocalDateTime createdAt;
    
    /**
     * 수정일시
     */
    @Column(name = "UPDATED_AT")
    private LocalDateTime updatedAt;
    
    /**
     * 엔티티가 저장되기 전 호출
     */
    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }
    
    /**
     * 엔티티가 업데이트되기 전 호출
     */
    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}

