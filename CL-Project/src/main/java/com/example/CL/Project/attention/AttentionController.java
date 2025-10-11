package com.example.CL.Project.attention;

import com.example.CL.Project.user.User;
import com.example.CL.Project.user.UserRepository;
import com.example.CL.Project.video.VideoChapter;
import com.example.CL.Project.video.VideoChapterRepository;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 시선 추적 집중도 API Controller
 */
@RestController
@RequestMapping("/api/attention")
public class AttentionController {

    @Autowired
    private UserAttentionLogRepository attentionLogRepo;

    @Autowired
    private ChapterAttentionAvgRepository attentionAvgRepo;

    @Autowired
    private UserRepository userRepo;

    @Autowired
    private VideoChapterRepository chapterRepo;

    /**
     * 챕터 시청 집중도 저장 API
     * - 기존 데이터보다 높은 집중도만 업데이트
     */
    @PostMapping("/save")
    public ResponseEntity<?> saveAttention(@RequestBody AttentionRequest request, HttpSession session) {
        System.out.println("\n[집중도 저장 요청]");
        System.out.println("  - chapterId: " + request.getChapterId());
        System.out.println("  - attentionScore: " + request.getAttentionScore());

        // SecurityContext에서 인증 정보 가져오기
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated() 
                || authentication.getPrincipal().equals("anonymousUser")) {
            System.out.println("  - 오류: 로그인되지 않음");
            return ResponseEntity.status(401).body(Map.of("error", "로그인 필요"));
        }
        
        String username = authentication.getName();
        System.out.println("  - 사용자: " + username);

        try {
            // 사용자 및 챕터 조회
            User user = userRepo.findByUsername(username)
                    .orElseThrow(() -> new RuntimeException("사용자를 찾을 수 없음"));
            VideoChapter chapter = chapterRepo.findById(request.getChapterId())
                    .orElseThrow(() -> new RuntimeException("챕터를 찾을 수 없음"));

            System.out.println("  - 사용자: " + user.getName() + " (ID: " + user.getUserId() + ")");
            System.out.println("  - 챕터: " + chapter.getTitle());

            // 기존 데이터 확인
            Optional<UserAttentionLog> existing = attentionLogRepo.findByUserAndChapter(user, chapter);

            Map<String, Object> response = new HashMap<>();

            if (existing.isPresent()) {
                UserAttentionLog log = existing.get();
                System.out.println("  - 기존 집중도: " + log.getAttentionScore());

                // 더 높은 집중도만 업데이트
                if (request.getAttentionScore() > log.getAttentionScore()) {
                    log.setAttentionScore(request.getAttentionScore());
                    log.setUpdatedAt(LocalDateTime.now());
                    attentionLogRepo.save(log);

                    System.out.println("  - ✅ 집중도 업데이트: " + request.getAttentionScore());

                    // 평균 집중도 재계산
                    updateChapterAverage(chapter);

                    response.put("updated", true);
                    response.put("score", log.getAttentionScore());
                    response.put("message", "집중도가 업데이트되었습니다");
                } else {
                    System.out.println("  - ⚠️ 기존 점수가 더 높음 (업데이트 안함)");
                    response.put("updated", false);
                    response.put("score", log.getAttentionScore());
                    response.put("message", "기존 점수가 더 높습니다");
                }
            } else {
                // 신규 데이터 저장
                UserAttentionLog log = new UserAttentionLog();
                log.setUser(user);
                log.setChapter(chapter);
                log.setAttentionScore(request.getAttentionScore());
                log.setCreatedAt(LocalDateTime.now());
                log.setUpdatedAt(LocalDateTime.now());
                attentionLogRepo.save(log);

                System.out.println("  - ✅ 신규 집중도 저장: " + request.getAttentionScore());

                // 평균 집중도 재계산
                updateChapterAverage(chapter);

                response.put("created", true);
                response.put("score", log.getAttentionScore());
                response.put("message", "집중도가 저장되었습니다");
            }

            return ResponseEntity.ok(response);

        } catch (Exception e) {
            System.out.println("  - ❌ 오류: " + e.getMessage());
            e.printStackTrace();
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * 챕터별 평균 집중도 재계산 및 업데이트
     */
    private void updateChapterAverage(VideoChapter chapter) {
        System.out.println("\n[평균 집중도 재계산]");
        System.out.println("  - 챕터: " + chapter.getTitle());

        // 해당 챕터의 모든 유저 집중도 가져오기
        List<UserAttentionLog> logs = attentionLogRepo.findByChapter(chapter);

        if (logs.isEmpty()) {
            System.out.println("  - ⚠️ 집중도 로그 없음");
            return;
        }

        // 평균 계산
        double avgScore = logs.stream()
                .mapToDouble(UserAttentionLog::getAttentionScore)
                .average()
                .orElse(0.0);

        System.out.println("  - 총 로그 수: " + logs.size());
        System.out.println("  - 평균 집중도: " + avgScore);

        // 평균 집중도 저장 또는 업데이트
        Optional<ChapterAttentionAvg> existing = attentionAvgRepo.findByChapter(chapter);

        if (existing.isPresent()) {
            ChapterAttentionAvg avg = existing.get();
            avg.setAvgAttentionScore(avgScore);
            avg.setTotalViews(logs.size());
            avg.setUpdatedAt(LocalDateTime.now());
            attentionAvgRepo.save(avg);
            System.out.println("  - ✅ 평균 집중도 업데이트 완료");
        } else {
            ChapterAttentionAvg avg = new ChapterAttentionAvg();
            avg.setChapter(chapter);
            avg.setAvgAttentionScore(avgScore);
            avg.setTotalViews(logs.size());
            avg.setUpdatedAt(LocalDateTime.now());
            attentionAvgRepo.save(avg);
            System.out.println("  - ✅ 평균 집중도 신규 생성 완료");
        }
    }

    /**
     * 특정 챕터의 평균 집중도 조회 API
     */
    @GetMapping("/chapter/{chapterId}/average")
    public ResponseEntity<?> getChapterAverage(@PathVariable Long chapterId) {
        System.out.println("\n[평균 집중도 조회]");
        System.out.println("  - chapterId: " + chapterId);

        try {
            VideoChapter chapter = chapterRepo.findById(chapterId)
                    .orElseThrow(() -> new RuntimeException("챕터를 찾을 수 없음"));

            Optional<ChapterAttentionAvg> avg = attentionAvgRepo.findByChapter(chapter);

            Map<String, Object> response = new HashMap<>();

            if (avg.isPresent()) {
                ChapterAttentionAvg avgData = avg.get();
                response.put("avgAttentionScore", avgData.getAvgAttentionScore());
                response.put("totalViews", avgData.getTotalViews());
                response.put("updatedAt", avgData.getUpdatedAt().toString());
                System.out.println("  - ✅ 평균: " + avgData.getAvgAttentionScore() + ", 시청수: " + avgData.getTotalViews());
            } else {
                response.put("avgAttentionScore", 0.0);
                response.put("totalViews", 0);
                System.out.println("  - ⚠️ 데이터 없음");
            }

            return ResponseEntity.ok(response);

        } catch (Exception e) {
            System.out.println("  - ❌ 오류: " + e.getMessage());
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }

    /**
     * 사용자의 특정 챕터 집중도 조회 API
     */
    @GetMapping("/user/chapter/{chapterId}")
    public ResponseEntity<?> getUserChapterAttention(@PathVariable Long chapterId, HttpSession session) {
        String username = (String) session.getAttribute("username");
        if (username == null) {
            return ResponseEntity.status(401).body(Map.of("error", "로그인 필요"));
        }

        try {
            User user = userRepo.findByUsername(username).orElseThrow();
            VideoChapter chapter = chapterRepo.findById(chapterId).orElseThrow();

            Optional<UserAttentionLog> log = attentionLogRepo.findByUserAndChapter(user, chapter);

            Map<String, Object> response = new HashMap<>();
            if (log.isPresent()) {
                response.put("attentionScore", log.get().getAttentionScore());
                response.put("updatedAt", log.get().getUpdatedAt().toString());
            } else {
                response.put("attentionScore", 0.0);
            }

            return ResponseEntity.ok(response);

        } catch (Exception e) {
            return ResponseEntity.status(500).body(Map.of("error", e.getMessage()));
        }
    }
}

