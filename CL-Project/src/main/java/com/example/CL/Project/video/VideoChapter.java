package com.example.CL.Project.video;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "VIDEO_CHAPTERS")
public class VideoChapter {
    
    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "chapter_seq")
    @SequenceGenerator(name = "chapter_seq", sequenceName = "CHAPTER_SEQ", allocationSize = 1)
    @Column(name = "CHAPTER_ID")
    private Long chapterId;
    
    @Column(name = "STORED_NAME", nullable = false, length = 500)
    private String storedName;
    
    @Column(name = "START_TIME", nullable = false)
    private Double startTime;
    
    @Column(name = "END_TIME", nullable = false)
    private Double endTime;
    
    @Column(name = "TITLE", nullable = false, length = 500)
    private String title;
    
    @Column(name = "SUMMARY", length = 2000)
    private String summary;
    
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
    public Long getChapterId() {
        return chapterId;
    }
    
    public void setChapterId(Long chapterId) {
        this.chapterId = chapterId;
    }
    
    public String getStoredName() {
        return storedName;
    }
    
    public void setStoredName(String storedName) {
        this.storedName = storedName;
    }
    
    public Double getStartTime() {
        return startTime;
    }
    
    public void setStartTime(Double startTime) {
        this.startTime = startTime;
    }
    
    public Double getEndTime() {
        return endTime;
    }
    
    public void setEndTime(Double endTime) {
        this.endTime = endTime;
    }
    
    public String getTitle() {
        return title;
    }
    
    public void setTitle(String title) {
        this.title = title;
    }
    
    public String getSummary() {
        return summary;
    }
    
    public void setSummary(String summary) {
        this.summary = summary;
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
}

