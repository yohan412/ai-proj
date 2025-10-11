package com.example.CL.Project.attention;

import com.example.CL.Project.video.VideoChapter;
import jakarta.persistence.*;
import java.time.LocalDateTime;

/**
 * 챕터별 평균 집중도 통계 엔티티
 */
@Entity
@Table(name = "CHAPTER_ATTENTION_AVG")
public class ChapterAttentionAvg {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "attention_avg_seq")
    @SequenceGenerator(name = "attention_avg_seq", sequenceName = "ATTENTION_AVG_SEQ", allocationSize = 1)
    @Column(name = "AVG_ID")
    private Long avgId;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "CHAPTER_ID", nullable = false, unique = true)
    private VideoChapter chapter;

    @Column(name = "AVG_ATTENTION_SCORE", nullable = false)
    private Double avgAttentionScore;

    @Column(name = "TOTAL_VIEWS", nullable = false)
    private Integer totalViews = 0;

    @Column(name = "UPDATED_AT", nullable = false)
    private LocalDateTime updatedAt;

    // ===== Constructors =====
    
    public ChapterAttentionAvg() {
        this.updatedAt = LocalDateTime.now();
        this.totalViews = 0;
    }

    // ===== Getters and Setters =====

    public Long getAvgId() {
        return avgId;
    }

    public void setAvgId(Long avgId) {
        this.avgId = avgId;
    }

    public VideoChapter getChapter() {
        return chapter;
    }

    public void setChapter(VideoChapter chapter) {
        this.chapter = chapter;
    }

    public Double getAvgAttentionScore() {
        return avgAttentionScore;
    }

    public void setAvgAttentionScore(Double avgAttentionScore) {
        this.avgAttentionScore = avgAttentionScore;
    }

    public Integer getTotalViews() {
        return totalViews;
    }

    public void setTotalViews(Integer totalViews) {
        this.totalViews = totalViews;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
}

