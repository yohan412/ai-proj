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
    public Video updateVideo(String storedName, SaveVideoRequest request) {
        // 기존 영상 조회
        Video video = videoRepository.findByStoredName(storedName)
                .orElseThrow(() -> new RuntimeException("영상을 찾을 수 없습니다: " + storedName));
        
        // userName만 업데이트 (storedName과 파일은 변경하지 않음)
        video.setUserName(request.getUserName());
        
        // duration 업데이트 (필요시)
        if (request.getDuration() != null) {
            video.setDuration(request.getDuration());
        }
        
        video = videoRepository.save(video);
        
        // 기존 챕터들 모두 삭제
        chapterRepository.deleteByStoredName(storedName);
        
        // 새 챕터들 저장
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
    
    public org.springframework.core.io.Resource getVideoResource(String storedName) throws IOException {
        Video video = videoRepository.findByStoredName(storedName)
                .orElseThrow(() -> new RuntimeException("영상을 찾을 수 없습니다: " + storedName));
        
        Path filePath = Paths.get(video.getFilePath());
        if (!Files.exists(filePath)) {
            throw new IOException("영상 파일이 존재하지 않습니다: " + filePath);
        }
        
        org.springframework.core.io.Resource resource = new org.springframework.core.io.UrlResource(filePath.toUri());
        if (resource.exists() && resource.isReadable()) {
            return resource;
        } else {
            throw new IOException("영상 파일을 읽을 수 없습니다: " + filePath);
        }
    }
}

