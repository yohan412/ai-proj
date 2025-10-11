package com.example.CL.Project.attention;

/**
 * 집중도 저장 요청 DTO
 */
public class AttentionRequest {
    
    private Long chapterId;
    private Double attentionScore;
    
    // ===== Constructors =====
    
    public AttentionRequest() {
    }
    
    public AttentionRequest(Long chapterId, Double attentionScore) {
        this.chapterId = chapterId;
        this.attentionScore = attentionScore;
    }
    
    // ===== Getters and Setters =====
    
    public Long getChapterId() {
        return chapterId;
    }
    
    public void setChapterId(Long chapterId) {
        this.chapterId = chapterId;
    }
    
    public Double getAttentionScore() {
        return attentionScore;
    }
    
    public void setAttentionScore(Double attentionScore) {
        this.attentionScore = attentionScore;
    }
}

