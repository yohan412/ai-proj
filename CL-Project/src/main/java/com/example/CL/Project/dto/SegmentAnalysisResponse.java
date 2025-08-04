package com.example.CL.Project.dto;

import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.util.List;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class SegmentAnalysisResponse {
    private List<String> labels;
    private List<Double> instantaneousLoadData;
    private List<Double> cumulativeLoadData;
}
