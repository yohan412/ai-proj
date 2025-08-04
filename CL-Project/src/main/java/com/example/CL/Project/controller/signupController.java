package com.example.CL.Project.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class signupController {

    @GetMapping({"/signup", "/signup.html"})
    public String showSignupPage() {
    return "signup"; 
    }
}
