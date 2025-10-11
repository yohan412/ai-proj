package com.example.CL.Project.user;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

/**
 * 인증 관련 컨트롤러
 * 회원가입, 로그인 등의 API 제공
 */
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
@Slf4j
public class AuthController {
    
    private final UserService userService;
    private final AuthenticationManager authenticationManager;
    
    /**
     * 회원가입 API
     * @param signUpRequest 회원가입 요청 데이터
     * @return 성공 메시지 또는 에러 메시지
     */
    @PostMapping("/signup")
    public ResponseEntity<?> signUp(@Valid @RequestBody SignUpRequest signUpRequest) {
        log.info("회원가입 API 호출: username={}", signUpRequest.getUsername());
        
        try {
            // 비밀번호 확인 체크
            if (!signUpRequest.getPassword().equals(signUpRequest.getPasswordConfirm())) {
                log.warn("비밀번호 불일치");
                return ResponseEntity.badRequest()
                        .body(createErrorResponse("비밀번호가 일치하지 않습니다."));
            }
            
            // 회원가입 처리
            User user = userService.signUp(signUpRequest);
            
            // 성공 응답 (비밀번호 제외)
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("message", "회원가입이 완료되었습니다.");
            response.put("userId", user.getUserId());
            response.put("username", user.getUsername());
            
            log.info("회원가입 성공: userId={}", user.getUserId());
            return ResponseEntity.status(HttpStatus.CREATED).body(response);
            
        } catch (IllegalArgumentException e) {
            log.error("회원가입 실패: {}", e.getMessage());
            return ResponseEntity.badRequest()
                    .body(createErrorResponse(e.getMessage()));
        } catch (Exception e) {
            log.error("회원가입 중 오류 발생", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(createErrorResponse("회원가입 처리 중 오류가 발생했습니다."));
        }
    }
    
    /**
     * 아이디 중복 확인 API
     * @param username 확인할 아이디
     * @return 중복 여부
     */
    @GetMapping("/check-username")
    public ResponseEntity<?> checkUsername(@RequestParam String username) {
        log.debug("아이디 중복 확인: {}", username);
        
        boolean isTaken = userService.isUsernameTaken(username);
        
        Map<String, Object> response = new HashMap<>();
        response.put("available", !isTaken);
        response.put("message", isTaken ? "이미 사용 중인 아이디입니다." : "사용 가능한 아이디입니다.");
        
        return ResponseEntity.ok(response);
    }
    
    /**
     * 이메일 중복 확인 API
     * @param email 확인할 이메일
     * @return 중복 여부
     */
    @GetMapping("/check-email")
    public ResponseEntity<?> checkEmail(@RequestParam String email) {
        log.debug("이메일 중복 확인: {}", email);
        
        boolean isTaken = userService.isEmailTaken(email);
        
        Map<String, Object> response = new HashMap<>();
        response.put("available", !isTaken);
        response.put("message", isTaken ? "이미 사용 중인 이메일입니다." : "사용 가능한 이메일입니다.");
        
        return ResponseEntity.ok(response);
    }
    
    /**
     * 로그인 API
     * @param loginRequest 로그인 요청 데이터
     * @param request HttpServletRequest (세션 생성용)
     * @return 성공 메시지 또는 에러 메시지
     */
    @PostMapping("/login")
    public ResponseEntity<?> login(@Valid @RequestBody LoginRequest loginRequest, HttpServletRequest request) {
        log.info("로그인 API 호출: username={}", loginRequest.getUsername());
        
        try {
            // Spring Security 인증 처리
            Authentication authentication = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(
                    loginRequest.getUsername(),
                    loginRequest.getPassword()
                )
            );
            
            // SecurityContext에 인증 정보 저장
            SecurityContext securityContext = SecurityContextHolder.getContext();
            securityContext.setAuthentication(authentication);
            
            // 세션에 SecurityContext 저장
            HttpSession session = request.getSession(true);
            session.setAttribute(HttpSessionSecurityContextRepository.SPRING_SECURITY_CONTEXT_KEY, securityContext);
            
            // 사용자 정보 조회
            User user = userService.findByUsername(loginRequest.getUsername());
            
            // 성공 응답
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("message", "로그인 성공");
            response.put("userId", user.getUserId());
            response.put("username", user.getUsername());
            response.put("name", user.getName());
            
            log.info("로그인 성공: userId={}, username={}", user.getUserId(), user.getUsername());
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            log.error("로그인 실패: {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(createErrorResponse("아이디 또는 비밀번호가 올바르지 않습니다."));
        }
    }
    
    /**
     * 로그아웃 API
     * Spring Security의 기본 로그아웃 기능을 사용하므로 이 메서드는 호출되지 않음
     * SecurityConfig에서 /api/auth/logout 경로를 Spring Security가 처리하도록 설정됨
     * 
     * @deprecated Spring Security의 로그아웃 필터가 처리
     */
    /*
    @PostMapping("/logout")
    public ResponseEntity<?> logout(HttpServletRequest request) {
        log.info("로그아웃 API 호출");
        
        // 세션 무효화
        HttpSession session = request.getSession(false);
        if (session != null) {
            session.invalidate();
        }
        
        // SecurityContext 클리어
        SecurityContextHolder.clearContext();
        
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "로그아웃 성공");
        
        log.info("로그아웃 성공");
        return ResponseEntity.ok(response);
    }
    */
    
    /**
     * 현재 로그인 상태 확인 API
     * @return 로그인 여부 및 사용자 정보
     */
    @GetMapping("/session")
    public ResponseEntity<?> checkSession() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        
        Map<String, Object> response = new HashMap<>();
        
        if (authentication != null && authentication.isAuthenticated() 
                && !authentication.getPrincipal().equals("anonymousUser")) {
            
            String username = authentication.getName();
            User user = userService.findByUsername(username);
            
            response.put("loggedIn", true);
            response.put("userId", user.getUserId());
            response.put("username", user.getUsername());
            response.put("name", user.getName());
            
            log.debug("세션 확인: 로그인 상태 - username={}", username);
        } else {
            response.put("loggedIn", false);
            log.debug("세션 확인: 비로그인 상태");
        }
        
        return ResponseEntity.ok(response);
    }
    
    /**
     * 현재 사용자 유형 조회 API
     * @return 사용자 유형 (admin, teacher, student, guest)
     */
    @GetMapping("/user-type")
    public ResponseEntity<?> getUserType() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        
        Map<String, Object> response = new HashMap<>();
        
        if (authentication != null && authentication.isAuthenticated() 
                && !authentication.getPrincipal().equals("anonymousUser")) {
            
            String username = authentication.getName();
            User user = userService.findByUsername(username);
            
            response.put("userType", user.getUserType());
            log.debug("사용자 타입 조회: username={}, userType={}", username, user.getUserType());
        } else {
            response.put("userType", "guest");
            log.debug("사용자 타입 조회: 비로그인 상태 (guest)");
        }
        
        return ResponseEntity.ok(response);
    }
    
    /**
     * 에러 응답 생성 헬퍼 메서드
     */
    private Map<String, Object> createErrorResponse(String message) {
        Map<String, Object> response = new HashMap<>();
        response.put("success", false);
        response.put("message", message);
        return response;
    }
}

