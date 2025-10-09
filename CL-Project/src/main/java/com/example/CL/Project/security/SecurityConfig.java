package com.example.CL.Project.security;

import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.ProviderManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Spring Security 설정
 * 비밀번호 암호화 및 인증/인가 설정
 */
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {
    
    private final UserDetailsService userDetailsService;
    
    /**
     * 비밀번호 암호화를 위한 BCryptPasswordEncoder Bean
     * BCrypt는 단방향 해시 함수로 비밀번호를 안전하게 저장
     * 
     * @return BCryptPasswordEncoder
     */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
    
    /**
     * AuthenticationManager Bean
     * 로그인 인증 처리를 위해 필요
     * 
     * @return AuthenticationManager
     */
    @Bean
    public AuthenticationManager authenticationManager() {
        DaoAuthenticationProvider authProvider = new DaoAuthenticationProvider();
        authProvider.setUserDetailsService(userDetailsService);
        authProvider.setPasswordEncoder(passwordEncoder());
        return new ProviderManager(authProvider);
    }
    
    /**
     * Spring Security 필터 체인 설정
     * 
     * @param http HttpSecurity
     * @return SecurityFilterChain
     * @throws Exception
     */
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            // CSRF 보호 설정
            .csrf(csrf -> csrf
                .ignoringRequestMatchers("/api/**")  // API 요청은 CSRF 검증 제외
            )
            
            // 요청 인가 설정
            .authorizeHttpRequests(auth -> auth
                // 정적 리소스는 모두 허용
                .requestMatchers(
                    "/css/**", 
                    "/js/**", 
                    "/images/**", 
                    "/webfonts/**",
                    "/sass/**"
                ).permitAll()
                
                // 공개 페이지 허용
                .requestMatchers(
                    "/", 
                    "/index", 
                    "/index.html"
                ).permitAll()
                
            // 인증 관련 API 허용
            .requestMatchers(
                "/api/auth/signup",
                "/api/auth/login",
                "/api/auth/logout",
                "/api/auth/session",
                "/api/auth/check-username",
                "/api/auth/check-email"
            ).permitAll()
                
                // Flask 연동 API 허용 (임시)
                .requestMatchers("/api/analyze").permitAll()
                
                // 영상 관리 API 허용 (임시)
                .requestMatchers("/api/videos/**").permitAll()
                
                // 영상 편집 페이지는 인증 필요 (나중에 활성화)
                .requestMatchers("/manage", "/generic").permitAll()  // 임시로 허용
                
                // 나머지 요청은 인증 필요
                .anyRequest().authenticated()
            )
            
            // 폼 로그인 설정 (기본 로그인 페이지 사용 안 함)
            .formLogin(form -> form.disable())
            
            // HTTP Basic 인증 비활성화
            .httpBasic(basic -> basic.disable())
            
            // 로그아웃 설정
            .logout(logout -> logout
                .logoutUrl("/api/auth/logout")
                .logoutSuccessUrl("/")
                .invalidateHttpSession(true)
                .deleteCookies("JSESSIONID")
                .permitAll()
            );
        
        return http.build();
    }
}

