package com.example.CL.Project.service;

import com.example.CL.Project.dto.EditedVideo;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class VideoService {
    public List<EditedVideo> getEditedVideos() {
        return List.of(
            new EditedVideo("/videos/edit1.mp4", "/thumbs/edit1.jpg", "Edit 01"),
            new EditedVideo("/videos/edit2.mp4", "/thumbs/edit2.jpg", "Edit 02"),
            new EditedVideo("/videos/edit3.mp4", "/thumbs/edit3.jpg", "Edit 03")
        );
    }
}