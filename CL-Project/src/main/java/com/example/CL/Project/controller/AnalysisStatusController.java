package com.example.CL.Project.controller;

import com.example.CL.Project.dto.AnalysisResult;
import com.example.CL.Project.dto.AnalysisStatusDto;
import com.example.CL.Project.service.InMemoryJobManager;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.File;
import java.io.IOException;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/jobs")
public class AnalysisStatusController {

    private final InMemoryJobManager jobManager;
    private final ObjectMapper objectMapper; // For reading JSON files

    @GetMapping("/{jobId}/status")
    public ResponseEntity<AnalysisStatusDto> getJobStatus(@PathVariable String jobId) {
        CompletableFuture<AnalysisResult> future = jobManager.getJob(jobId);

        if (future == null) {
            return ResponseEntity.notFound().build();
        }

        if (future.isDone()) {
            if (future.isCompletedExceptionally()) {
                try {
                    future.get(); // This will rethrow the exception
                    return ResponseEntity.ok(AnalysisStatusDto.failed("Unknown error"));
                } catch (Exception e) {
                    return ResponseEntity.ok(AnalysisStatusDto.failed(e.getMessage()));
                }
            } else {
                AnalysisResult result = future.getNow(null);
                Map<String, String> resultPaths = Map.of(
                        "transcriptPath", result.transcriptPath(),
                        "graphPath", result.graphPath(),
                        "cognitiveLoadPath", result.cognitiveLoadPath()
                );
                return ResponseEntity.ok(AnalysisStatusDto.completed(resultPaths));
            }
        }

        return ResponseEntity.ok(AnalysisStatusDto.processing());
    }

    @GetMapping("/{jobId}/graph")
    public ResponseEntity<Resource> getGraphData(@PathVariable String jobId) throws IOException {
        Resource resource = new FileSystemResource("uploads/" + jobId + "_graph.json");
        if (!resource.exists()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON).body(resource);
    }

    @GetMapping("/{jobId}/cognitive-load")
    public ResponseEntity<Resource> getCognitiveLoadData(@PathVariable String jobId) throws IOException {
        Resource resource = new FileSystemResource("uploads/" + jobId + "_cognitive_load.json");
        if (!resource.exists()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON).body(resource);
    }
}
