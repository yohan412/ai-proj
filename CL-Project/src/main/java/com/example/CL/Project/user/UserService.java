package com.example.CL.Project.user;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 사용자 서비스
 * 회원가입, 로그인 등 사용자 관련 비즈니스 로직 처리
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class UserService {
    
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    
    /**
     * 회원가입
     * @param signUpRequest 회원가입 요청 DTO
     * @return 생성된 사용자
     * @throws IllegalArgumentException 아이디나 이메일이 중복된 경우
     */
    @Transactional
    public User signUp(SignUpRequest signUpRequest) {
        log.info("회원가입 시도: username={}, email={}", signUpRequest.getUsername(), signUpRequest.getEmail());
        
        // 아이디 중복 확인
        if (userRepository.existsByUsername(signUpRequest.getUsername())) {
            log.warn("아이디 중복: {}", signUpRequest.getUsername());
            throw new IllegalArgumentException("이미 사용 중인 아이디입니다.");
        }
        
        // 이메일 중복 확인
        if (userRepository.existsByEmail(signUpRequest.getEmail())) {
            log.warn("이메일 중복: {}", signUpRequest.getEmail());
            throw new IllegalArgumentException("이미 사용 중인 이메일입니다.");
        }
        
        // 비밀번호 암호화
        String encodedPassword = passwordEncoder.encode(signUpRequest.getPassword());
        log.debug("비밀번호 암호화 완료");
        
        // User 엔티티 생성
        User user = User.builder()
                .name(signUpRequest.getName())
                .email(signUpRequest.getEmail())
                .organization(signUpRequest.getOrganization())
                .username(signUpRequest.getUsername())
                .password(encodedPassword)  // 암호화된 비밀번호 저장
                .enabled(true)
                .build();
        
        // DB에 저장
        User savedUser = userRepository.save(user);
        log.info("회원가입 성공: userId={}, username={}", savedUser.getUserId(), savedUser.getUsername());
        
        return savedUser;
    }
    
    /**
     * 아이디로 사용자 조회
     * @param username 아이디
     * @return User
     * @throws IllegalArgumentException 사용자를 찾을 수 없는 경우
     */
    public User findByUsername(String username) {
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다: " + username));
    }
    
    /**
     * 아이디 중복 확인
     * @param username 아이디
     * @return 중복 여부 (true: 중복, false: 사용 가능)
     */
    public boolean isUsernameTaken(String username) {
        return userRepository.existsByUsername(username);
    }
    
    /**
     * 이메일 중복 확인
     * @param email 이메일
     * @return 중복 여부 (true: 중복, false: 사용 가능)
     */
    public boolean isEmailTaken(String email) {
        return userRepository.existsByEmail(email);
    }
}

