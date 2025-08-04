package com.example.CL.Project.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import com.example.CL.Project.dto.LoginForm;

@Controller
public class MainController {

    @GetMapping({ "/", "/main" })
    public String mainPage(Model model) {
        model.addAttribute("loginForm", new LoginForm());
        return "main";
    }
}