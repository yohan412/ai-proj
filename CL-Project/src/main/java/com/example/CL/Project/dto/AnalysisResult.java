package com.example.CL.Project.dto;

/**
 * A simple, immutable data carrier object to hold the results of a video analysis.
 * This record is used to pass the file paths of the generated analysis files
 * (transcript, graph, cognitive load) from the analysis service to the job manager.
 * It exists only in memory for the duration of an analysis job.
 */
public record AnalysisResult(
    String transcriptPath,
    String graphPath,
    String cognitiveLoadPath,
    String strDataPath
) {}
