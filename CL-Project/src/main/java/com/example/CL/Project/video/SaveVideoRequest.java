package com.example.CL.Project.video;

import java.util.List;

public class SaveVideoRequest {
    private String userName;
    private Double duration;
    private List<ChapterData> chapters;
    
    public static class ChapterData {
        private Double start;
        private Double end;
        private String title;
        private String summary;
        
        public Double getStart() {
            return start;
        }
        
        public void setStart(Double start) {
            this.start = start;
        }
        
        public Double getEnd() {
            return end;
        }
        
        public void setEnd(Double end) {
            this.end = end;
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
    }
    
    public String getUserName() {
        return userName;
    }
    
    public void setUserName(String userName) {
        this.userName = userName;
    }
    
    public Double getDuration() {
        return duration;
    }
    
    public void setDuration(Double duration) {
        this.duration = duration;
    }
    
    public List<ChapterData> getChapters() {
        return chapters;
    }
    
    public void setChapters(List<ChapterData> chapters) {
        this.chapters = chapters;
    }
}

