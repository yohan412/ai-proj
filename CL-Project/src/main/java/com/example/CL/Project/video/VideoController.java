package com.example.CL.Project.video;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/videos")
public class VideoController {
    
    private final VideoService videoService;
    
    public VideoController(VideoService videoService) {
        this.videoService = videoService;
    }
    
    @PostMapping("/save")
    public ResponseEntity<?> saveVideo(
            @RequestParam("file") MultipartFile file,
            @RequestParam("userName") String userName,
            @RequestParam(value = "duration", required = false, defaultValue = "0") Double duration,
            @RequestParam(value = "chapters", required = false) String chaptersJson) {
        
        System.out.println("====================================");
        System.out.println("🔵 영상 저장 요청 수신");
        System.out.println("  - 파일명: " + file.getOriginalFilename());
        System.out.println("  - 파일 크기: " + file.getSize() + " bytes");
        System.out.println("  - 사용자 이름: " + userName);
        System.out.println("  - 영상 길이: " + duration + " 초");
        System.out.println("  - 챕터 JSON 길이: " + (chaptersJson != null ? chaptersJson.length() : 0));
        System.out.println("====================================");
        
        try {
            // JSON 문자열을 SaveVideoRequest로 변환
            SaveVideoRequest request = new SaveVideoRequest();
            request.setUserName(userName);
            request.setDuration(duration);
            
            // chaptersJson 파싱
            if (chaptersJson != null && !chaptersJson.trim().isEmpty()) {
                System.out.println("📝 챕터 JSON 파싱 시작...");
                System.out.println("챕터 JSON: " + chaptersJson.substring(0, Math.min(200, chaptersJson.length())) + "...");
                
                com.fasterxml.jackson.databind.ObjectMapper objectMapper = new com.fasterxml.jackson.databind.ObjectMapper();
                List<SaveVideoRequest.ChapterData> chapters = objectMapper.readValue(
                    chaptersJson, 
                    objectMapper.getTypeFactory().constructCollectionType(List.class, SaveVideoRequest.ChapterData.class)
                );
                request.setChapters(chapters);
                System.out.println("✅ 챕터 파싱 완료: " + chapters.size() + "개");
            } else {
                System.out.println("⚠️ 챕터 정보 없음");
            }
            
            System.out.println("💾 VideoService.saveVideo 호출...");
            Video savedVideo = videoService.saveVideo(file, request);
            System.out.println("✅ 저장 완료!");
            System.out.println("  - Video ID: " + savedVideo.getVideoId());
            System.out.println("  - Stored Name: " + savedVideo.getStoredName());
            
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("message", "영상이 저장되었습니다.");
            response.put("videoId", savedVideo.getVideoId());
            response.put("storedName", savedVideo.getStoredName());
            
            System.out.println("📤 응답 전송: " + response);
            return ResponseEntity.ok(response);
            
        } catch (Exception e) {
            System.err.println("❌ 저장 실패!");
            System.err.println("오류 메시지: " + e.getMessage());
            e.printStackTrace();
            
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("success", false);
            errorResponse.put("message", "영상 저장 실패: " + e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }
    
    @GetMapping("/{storedName}")
    public ResponseEntity<?> getVideo(@PathVariable String storedName) {
        try {
            Video video = videoService.getVideoByStoredName(storedName);
            List<VideoChapter> chapters = videoService.getChaptersByStoredName(storedName);
            
            Map<String, Object> response = new HashMap<>();
            response.put("video", video);
            response.put("chapters", chapters);
            
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("success", false);
            errorResponse.put("message", e.getMessage());
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(errorResponse);
        }
    }
    
    @GetMapping
    public ResponseEntity<?> getAllVideos() {
        try {
            List<Video> videos = videoService.getAllVideos();
            return ResponseEntity.ok(videos);
        } catch (Exception e) {
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("success", false);
            errorResponse.put("message", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }
    
    @DeleteMapping("/{videoId}")
    public ResponseEntity<?> deleteVideo(@PathVariable Long videoId) {
        try {
            videoService.deleteVideo(videoId);
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("message", "영상이 삭제되었습니다.");
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("success", false);
            errorResponse.put("message", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }
    
    @GetMapping("/stream/{storedName}")
    public ResponseEntity<?> streamVideo(@PathVariable String storedName) {
        try {
            System.out.println("🎬 영상 스트리밍 요청: " + storedName);
            org.springframework.core.io.Resource resource = videoService.getVideoResource(storedName);
            
            return ResponseEntity.ok()
                    .contentType(org.springframework.http.MediaType.parseMediaType("video/mp4"))
                    .header("Content-Disposition", "inline; filename=\"" + storedName + "\"")
                    .body(resource);
        } catch (Exception e) {
            System.err.println("❌ 영상 스트리밍 실패: " + e.getMessage());
            Map<String, Object> errorResponse = new HashMap<>();
            errorResponse.put("success", false);
            errorResponse.put("message", e.getMessage());
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(errorResponse);
        }
    }
}

