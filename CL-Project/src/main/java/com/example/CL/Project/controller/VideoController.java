package com.example.CL.Project.controller;

import com.example.CL.Project.dto.AnalysisResult;
import com.example.CL.Project.service.InMemoryJobManager;
import com.example.CL.Project.service.VideoAnalysisService;
import com.example.CL.Project.util.FileCompareUtil;
import jakarta.validation.constraints.NotNull;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/videos")
public class VideoController {

    private final VideoAnalysisService videoAnalysisService;
    private final InMemoryJobManager jobManager;
    private final String UPLOAD_DIR = "uploads/";

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<Map<String, String>> upload(@RequestPart("file") @NotNull MultipartFile file, @AuthenticationPrincipal UserDetails userDetails) {
        String currentUsername = userDetails.getUsername();
        String originalFilename = file.getOriginalFilename();

        // Handle cases where the filename might be null or empty
        if (originalFilename == null || originalFilename.isBlank()) {
            // If there's no filename, we cannot check for duplicates, so proceed to analysis
            String jobId = videoAnalysisService.analyzeVideo(file, currentUsername);
            Map<String, String> response = new HashMap<>();
            response.put("jobId", jobId);
            return ResponseEntity.ok(response);
        }

        // Create a highly specific search prefix (e.g., "dongl_lecture")
        String filenameWithoutExtension = originalFilename;
        int dotIndex = originalFilename.lastIndexOf('.');
        if (dotIndex > 0) {
            filenameWithoutExtension = originalFilename.substring(0, dotIndex);
        }
        String searchPrefix = currentUsername + "_" + filenameWithoutExtension;

        File uploadDir = new File(UPLOAD_DIR);

        // This filter is now hyper-specific, only finding files that originated from the same filename for that user.
        java.io.FilenameFilter userFileFilter = (dir, name) -> name.startsWith(searchPrefix) && name.endsWith(".mp4");
        File[] candidateFiles = uploadDir.listFiles(userFileFilter);

        // This loop now only iterates over a very small set of candidate files.
        if (candidateFiles != null) {
            for (File existingFile : candidateFiles) {
                try {
                    if (FileCompareUtil.isSameFile(file, existingFile.getAbsolutePath())) {
                        String jobId = existingFile.getName().substring(0, existingFile.getName().lastIndexOf('.'));

                        // Duplicate content found, re-register the job and return the existing jobId.
                        CompletableFuture<AnalysisResult> future = new CompletableFuture<>();
                        Path uploadPath = Paths.get(UPLOAD_DIR);
                        AnalysisResult result = new AnalysisResult(
                                uploadPath.resolve(jobId + "_transcript.json").toString(),
                                uploadPath.resolve(jobId + "_graph.json").toString(),
                                uploadPath.resolve(jobId + "_cognitive_load.json").toString(),
                                uploadPath.resolve(jobId + "_str_data.json").toString()
                        );
                        future.complete(result);
                        jobManager.submitJob(jobId, future);

                        Map<String, String> response = new HashMap<>();
                        response.put("jobId", jobId);
                        return ResponseEntity.ok(response);
                    }
                } catch (Exception e) {
                    System.err.println("Error comparing file '" + file.getOriginalFilename() + "' with '" + existingFile.getName() + "': " + e.getMessage());
                }
            }
        }

        // If no duplicate content is found, start a new analysis.
        String jobId = videoAnalysisService.analyzeVideo(file, currentUsername);
        Map<String, String> response = new HashMap<>();
        response.put("jobId", jobId);
        return ResponseEntity.ok(response);
    }
}
