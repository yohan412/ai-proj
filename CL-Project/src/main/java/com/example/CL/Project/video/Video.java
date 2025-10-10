package com.example.CL.Project.video;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "VIDEOS")
public class Video {
    
    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "video_seq")
    @SequenceGenerator(name = "video_seq", sequenceName = "VIDEO_SEQ", allocationSize = 1)
    @Column(name = "VIDEO_ID")
    private Long videoId;
    
    @Column(name = "STORED_NAME", nullable = false, unique = true, length = 500)
    private String storedName;
    
    @Column(name = "USER_NAME", nullable = false, length = 200)
    private String userName;
    
    @Column(name = "FILE_PATH", nullable = false, length = 1000)
    private String filePath;
    
    @Column(name = "DURATION", nullable = false)
    private Double duration = 0.0;
    
    @Lob
    @Column(name = "SEGMENTS", columnDefinition = "CLOB")
    private String segments;  // JSON 형식의 자막 세그먼트
    
    @Column(name = "DETECTED_LANG", length = 10)
    private String detectedLang;  // 감지된 언어 (예: "ko", "en", "ja")
    
    @Column(name = "CREATED_AT", nullable = false, updatable = false)
    private LocalDateTime createdAt;
    
    @Column(name = "UPDATED_AT", nullable = false)
    private LocalDateTime updatedAt;
    
    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }
    
    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
    
    // Getters and Setters
    public Long getVideoId() {
        return videoId;
    }
    
    public void setVideoId(Long videoId) {
        this.videoId = videoId;
    }
    
    public String getStoredName() {
        return storedName;
    }
    
    public void setStoredName(String storedName) {
        this.storedName = storedName;
    }
    
    public String getUserName() {
        return userName;
    }
    
    public void setUserName(String userName) {
        this.userName = userName;
    }
    
    public String getFilePath() {
        return filePath;
    }
    
    public void setFilePath(String filePath) {
        this.filePath = filePath;
    }
    
    public Double getDuration() {
        return duration;
    }
    
    public void setDuration(Double duration) {
        this.duration = duration;
    }
    
    public LocalDateTime getCreatedAt() {
        return createdAt;
    }
    
    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
    
    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }
    
    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
    
    public String getSegments() {
        return segments;
    }
    
    public void setSegments(String segments) {
        this.segments = segments;
    }
    
    public String getDetectedLang() {
        return detectedLang;
    }
    
    public void setDetectedLang(String detectedLang) {
        this.detectedLang = detectedLang;
    }
}

