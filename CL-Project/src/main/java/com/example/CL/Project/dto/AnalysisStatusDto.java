package com.example.CL.Project.dto;

import lombok.Data;
import lombok.RequiredArgsConstructor;

import java.util.Map;

@Data
@RequiredArgsConstructor
public class AnalysisStatusDto {
    private final String status;
    private final Map<String, String> result; // e.g., {"transcriptPath": "...", "graphPath": "..."}
    private final String errorMessage;

    public static AnalysisStatusDto processing() {
        return new AnalysisStatusDto("PROCESSING", null, null);
    }

    public static AnalysisStatusDto completed(Map<String, String> result) {
        return new AnalysisStatusDto("COMPLETED", result, null);
    }

    public static AnalysisStatusDto failed(String errorMessage) {
        return new AnalysisStatusDto("FAILED", null, errorMessage);
    }
}
