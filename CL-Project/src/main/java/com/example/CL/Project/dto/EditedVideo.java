package com.example.CL.Project.dto;

public class EditedVideo {
    private String videoUrl;
    private String thumbnailUrl;
    private String label;

    public EditedVideo(String videoUrl, String thumbnailUrl, String label) {
        this.videoUrl = videoUrl;
        this.thumbnailUrl = thumbnailUrl;
        this.label = label;
    }

    public String getVideoUrl() { return videoUrl; }
    public String getThumbnailUrl() { return thumbnailUrl; }
    public String getLabel() { return label; }
}