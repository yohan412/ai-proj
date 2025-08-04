package com.example.CL.Project.dto;

import lombok.AllArgsConstructor;
import lombok.*;

import java.time.LocalDateTime;

@Data
@AllArgsConstructor
@NoArgsConstructor 
@Builder
public class AnnouncementDto {
    private Long id;
    private String title;
    private String writer;
    private String password;
    private String content;
    private LocalDateTime createdAt;
    private int viewCount;
}
