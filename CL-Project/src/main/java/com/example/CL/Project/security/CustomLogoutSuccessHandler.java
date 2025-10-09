package com.example.CL.Project.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.core.Authentication;
import org.springframework.security.web.authentication.logout.LogoutSuccessHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/**
 * 커스텀 로그아웃 성공 핸들러
 * 로그아웃 성공 시 JSON 응답을 반환
 */
@Component
@Slf4j
public class CustomLogoutSuccessHandler implements LogoutSuccessHandler {
    
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    @Override
    public void onLogoutSuccess(HttpServletRequest request, HttpServletResponse response, 
                                Authentication authentication) throws IOException, ServletException {
        
        log.info("로그아웃 성공 핸들러 호출");
        
        // JSON 응답 설정
        response.setStatus(HttpServletResponse.SC_OK);
        response.setContentType("application/json");
        response.setCharacterEncoding("UTF-8");
        
        // 응답 데이터 생성
        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("message", "로그아웃 성공");
        
        // JSON으로 변환하여 응답
        String json = objectMapper.writeValueAsString(result);
        response.getWriter().write(json);
        
        log.info("로그아웃 성공 응답 전송 완료");
    }
}

