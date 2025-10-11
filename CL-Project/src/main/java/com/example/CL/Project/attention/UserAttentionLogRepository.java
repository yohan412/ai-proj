package com.example.CL.Project.attention;

import com.example.CL.Project.user.User;
import com.example.CL.Project.video.VideoChapter;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * 사용자별 챕터 집중도 로그 Repository
 */
@Repository
public interface UserAttentionLogRepository extends JpaRepository<UserAttentionLog, Long> {
    
    /**
     * 특정 사용자와 챕터로 로그 조회
     */
    Optional<UserAttentionLog> findByUserAndChapter(User user, VideoChapter chapter);
    
    /**
     * 특정 챕터의 모든 집중도 로그 조회
     */
    List<UserAttentionLog> findByChapter(VideoChapter chapter);
    
    /**
     * 특정 사용자의 모든 집중도 로그 조회
     */
    List<UserAttentionLog> findByUser(User user);
}

