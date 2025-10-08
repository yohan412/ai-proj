package com.example.CL.Project.user;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * 사용자 Repository
 * JPA를 통해 USERS 테이블에 접근
 */
@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    
    /**
     * 아이디로 사용자 조회
     * @param username 아이디
     * @return Optional<User>
     */
    Optional<User> findByUsername(String username);
    
    /**
     * 이메일로 사용자 조회
     * @param email 이메일
     * @return Optional<User>
     */
    Optional<User> findByEmail(String email);
    
    /**
     * 아이디 존재 여부 확인
     * @param username 아이디
     * @return 존재 여부
     */
    boolean existsByUsername(String username);
    
    /**
     * 이메일 존재 여부 확인
     * @param email 이메일
     * @return 존재 여부
     */
    boolean existsByEmail(String email);
}

