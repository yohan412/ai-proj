package com.example.CL.Project.controller;

import com.example.CL.Project.dto.EditedVideo;
import com.example.CL.Project.service.VideoService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;

@Controller
@RequiredArgsConstructor
public class DeepAnalyzerController {

    private final VideoService videoService;

    @GetMapping("/deepAnalyzer")
    public String showDeepAnalyzer(@RequestParam(value = "video", required = false) String storedName,
                                   Model model) {
        List<EditedVideo> editedVideos = videoService.getEditedVideos();
        model.addAttribute("editedVideos", editedVideos);

        if (storedName != null && !storedName.isBlank()&& !storedName.equals("undefined")) {
            String videoUrl = "/api/videos/" + storedName;
            model.addAttribute("videoUrl", videoUrl);
        }

        return "DeepAnalyzer"; 
    }
}