package com.example.CL.Project.controller;

import com.example.CL.Project.dto.*; // SegmentAnalysisRequest, SegmentAnalysisResponse
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.http.*; // HttpEntity, HttpHeaders, MediaType, ResponseEntity
import org.springframework.web.bind.annotation.*; // PostMapping, RequestBody, RequestMapping, RestController
import org.springframework.web.client.RestTemplate;

import java.util.*; // Collections, HashMap, List, Map

@RestController
@RequestMapping("/api/videos")
@RequiredArgsConstructor
public class EditedVideoController {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    private final String PYTHON_MICROSERVICE_URL = "http://localhost:5000"; // Python microservice URL

    @PostMapping("/analyze-segment")
    public ResponseEntity<SegmentAnalysisResponse> analyzeSegment(@RequestBody SegmentAnalysisRequest request) {
        System.out.println("Received segment analysis request:");
        System.out.println("Job ID: " + request.getJobId());
        System.out.println("Start Time: " + request.getStart());
        System.out.println("End Time: " + request.getEnd());

        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setAccept(Collections.singletonList(MediaType.APPLICATION_JSON));

            Map<String, Object> pythonRequestBody = new HashMap<>();
            pythonRequestBody.put("jobId", request.getJobId());
            pythonRequestBody.put("startTime", request.getStart());
            pythonRequestBody.put("endTime", request.getEnd());

            HttpEntity<Map<String, Object>> pythonRequest = new HttpEntity<>(pythonRequestBody, headers);

            ResponseEntity<Map> pythonAnalysisResponse = restTemplate.postForEntity(
                    PYTHON_MICROSERVICE_URL + "/analyze_segment", pythonRequest, Map.class);

            if (pythonAnalysisResponse.getStatusCode().is2xxSuccessful() && pythonAnalysisResponse.getBody() != null) {
                Map<String, Object> responseData = pythonAnalysisResponse.getBody();
                Map<String, Object> cognitiveLoadData = (Map<String, Object>) responseData.get("cognitiveLoad");

                List<String> labels = (List<String>) cognitiveLoadData.get("labels");
                List<Double> instantaneousLoadData = (List<Double>) cognitiveLoadData.get("instantaneousLoadData");
                List<Double> cumulativeLoadData = (List<Double>) cognitiveLoadData.get("cumulativeLoadData");

                SegmentAnalysisResponse response = new SegmentAnalysisResponse(labels, instantaneousLoadData, cumulativeLoadData);
                return ResponseEntity.ok(response);
            } else {
                System.err.println("Python microservice segment analysis failed: " + pythonAnalysisResponse.getStatusCode());
                return ResponseEntity.status(pythonAnalysisResponse.getStatusCode()).body(new SegmentAnalysisResponse(Collections.emptyList(), Collections.emptyList(), Collections.emptyList()));
            }

        } catch (Exception e) {
            System.err.println("Error during segment analysis: " + e.getMessage());
            e.printStackTrace();
            return ResponseEntity.status(500).body(new SegmentAnalysisResponse(Collections.emptyList(), Collections.emptyList(), Collections.emptyList()));
        }
    }
}

