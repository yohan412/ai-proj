package com.example.CL.Project.config;

import com.example.CL.Project.dto.LoginForm;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ModelAttribute;

@ControllerAdvice
public class GlobalModelAttributeAdvice {

    @ModelAttribute("loginForm")
    public LoginForm loginForm() {
        return new LoginForm();
    }
}
