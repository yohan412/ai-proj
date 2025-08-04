package com.example.CL.Project.dto;

import lombok.Data;

@Data
public class SegmentAnalysisRequest {
    private String jobId;
    private double start;
    private double end;
}
