package com.example.CL.Project.video;


import java.util.List;

public class AnalyzeResponse {
  private String format;          // "json"
  private Double duration;        // 초
  private List<Segment> segments; // Whisper 원본
  private List<Chapter> chapters; // gpt-oss-20b로 구간화
  private String text;            // (백업 필드)

  public String getFormat() { return format; }
  public void setFormat(String format) { this.format = format; }
  public Double getDuration() { return duration; }
  public void setDuration(Double duration) { this.duration = duration; }
  public List<Segment> getSegments() { return segments; }
  public void setSegments(List<Segment> segments) { this.segments = segments; }
  public List<Chapter> getChapters() { return chapters; }
  public void setChapters(List<Chapter> chapters) { this.chapters = chapters; }
  public String getText() { return text; }
  public void setText(String text) { this.text = text; }
}