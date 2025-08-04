package com.example.CL.Project.service;

import com.example.CL.Project.dto.AnalysisResult;
import org.springframework.web.multipart.MultipartFile;

import java.util.concurrent.CompletableFuture;

public interface VideoAnalysisService {
    String analyzeVideo(MultipartFile file, String username);
}
