package com.example.CL.Project.video;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;

@Service
public class VideoService {
    
    private final VideoRepository videoRepository;
    private final VideoChapterRepository chapterRepository;
    
    @Value("${media.video-upload-path:./upload}")
    private String uploadPath;
    
    public VideoService(VideoRepository videoRepository, VideoChapterRepository chapterRepository) {
        this.videoRepository = videoRepository;
        this.chapterRepository = chapterRepository;
    }
    
    @Transactional
    public Video saveVideo(MultipartFile file, SaveVideoRequest request) throws IOException {
        // 업로드 폴더 생성
        File uploadDir = new File(uploadPath);
        if (!uploadDir.exists()) {
            uploadDir.mkdirs();
        }
        
        // 고유한 파일명 생성: 사용자입력이름_현재시간일정.확장자
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS"));
        String originalFilename = file.getOriginalFilename();
        String extension = "";
        if (originalFilename != null && originalFilename.contains(".")) {
            extension = originalFilename.substring(originalFilename.lastIndexOf("."));
        }
        String storedName = sanitizeFilename(request.getUserName()) + "_" + timestamp + extension;
        
        // 파일 저장
        Path filePath = Paths.get(uploadPath, storedName);
        Files.copy(file.getInputStream(), filePath, StandardCopyOption.REPLACE_EXISTING);
        
        // Video 엔티티 생성
        Video video = new Video();
        video.setStoredName(storedName);
        video.setUserName(request.getUserName());
        video.setFilePath(filePath.toString());
        video.setDuration(request.getDuration() != null ? request.getDuration() : 0.0);
        
        // 먼저 Video 저장
        video = videoRepository.save(video);
        
        // Chapter 엔티티들 생성 및 저장
        if (request.getChapters() != null && !request.getChapters().isEmpty()) {
            for (SaveVideoRequest.ChapterData chapterData : request.getChapters()) {
                VideoChapter chapter = new VideoChapter();
                chapter.setStoredName(storedName);
                chapter.setStartTime(chapterData.getStart());
                chapter.setEndTime(chapterData.getEnd());
                chapter.setTitle(chapterData.getTitle());
                chapter.setSummary(chapterData.getSummary());
                chapterRepository.save(chapter);
            }
        }
        
        return video;
    }
    
    public Video getVideoByStoredName(String storedName) {
        return videoRepository.findByStoredName(storedName)
                .orElseThrow(() -> new RuntimeException("영상을 찾을 수 없습니다: " + storedName));
    }
    
    public List<VideoChapter> getChaptersByStoredName(String storedName) {
        return chapterRepository.findByStoredNameOrderByStartTimeAsc(storedName);
    }
    
    public List<Video> getAllVideos() {
        return videoRepository.findAll();
    }
    
    @Transactional
    public void deleteVideo(Long videoId) {
        Video video = videoRepository.findById(videoId)
                .orElseThrow(() -> new RuntimeException("영상을 찾을 수 없습니다: " + videoId));
        
        // 파일 삭제
        try {
            Path filePath = Paths.get(video.getFilePath());
            Files.deleteIfExists(filePath);
        } catch (IOException e) {
            System.err.println("파일 삭제 실패: " + e.getMessage());
        }
        
        // DB에서 삭제 (CASCADE로 챕터도 자동 삭제)
        videoRepository.delete(video);
    }
    
    private String sanitizeFilename(String filename) {
        // 파일명에서 특수문자 제거
        return filename.replaceAll("[^a-zA-Z0-9가-힣\\-_]", "_");
    }
}

