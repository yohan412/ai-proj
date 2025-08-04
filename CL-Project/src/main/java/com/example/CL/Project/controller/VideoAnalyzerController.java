package com.example.CL.Project.controller;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

/**
 * VideoAnalyzerController
 *
 * This controller handles requests related to the video analysis page.
 * It primarily serves the `VidAnalyzer.html` Thymeleaf template,
 * which is the main interface for users to upload videos and view analysis results.
 */
@Controller
public class VideoAnalyzerController {

    private final ObjectMapper mapper = new ObjectMapper();


    /**
     * Handles GET requests for the "/analyze" endpoint.
     * This method prepares the model for the `VidAnalyzer.html` template,
     * including adding a `LoginForm` object to the model for login functionality
     * within the page.
     *
     * @param model The Spring UI model to which attributes can be added.
     * @return The name of the Thymeleaf template to render, which is "VidAnalyzer".
     * @throws JsonProcessingException If there's an error during JSON processing (though not directly used here, kept for consistency).
     */
    @GetMapping("/analyze")
    public String videoAnalyzerPage(@RequestParam(required = false) String jobId, Model model) throws JsonProcessingException {

        /* ---------- 5) (already in your template) ---------- */
        // Adds a LoginForm object to the model. This is typically used for rendering
        // a login form fragment within the VidAnalyzer page, allowing users to log in.
        model.addAttribute("loginForm", new com.example.CL.Project.dto.LoginForm());
        if (jobId != null) {
            model.addAttribute("jobId", jobId);
        }

        return "VidAnalyzer";
    }
}