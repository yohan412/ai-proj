package com.example.CL.Project.attention;

import com.example.CL.Project.user.User;
import com.example.CL.Project.video.VideoChapter;
import jakarta.persistence.*;
import java.time.LocalDateTime;

/**
 * 사용자별 챕터 시청 집중도 로그 엔티티
 */
@Entity
@Table(name = "USER_ATTENTION_LOGS")
public class UserAttentionLog {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "attention_log_seq")
    @SequenceGenerator(name = "attention_log_seq", sequenceName = "ATTENTION_LOG_SEQ", allocationSize = 1)
    @Column(name = "LOG_ID")
    private Long logId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "USER_ID", nullable = false)
    private User user;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "CHAPTER_ID", nullable = false)
    private VideoChapter chapter;

    @Column(name = "ATTENTION_SCORE", nullable = false)
    private Double attentionScore;

    @Column(name = "CREATED_AT", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "UPDATED_AT", nullable = false)
    private LocalDateTime updatedAt;

    // ===== Constructors =====
    
    public UserAttentionLog() {
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    // ===== Getters and Setters =====

    public Long getLogId() {
        return logId;
    }

    public void setLogId(Long logId) {
        this.logId = logId;
    }

    public User getUser() {
        return user;
    }

    public void setUser(User user) {
        this.user = user;
    }

    public VideoChapter getChapter() {
        return chapter;
    }

    public void setChapter(VideoChapter chapter) {
        this.chapter = chapter;
    }

    public Double getAttentionScore() {
        return attentionScore;
    }

    public void setAttentionScore(Double attentionScore) {
        this.attentionScore = attentionScore;
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

    @PrePersist
    protected void onCreate() {
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
}

