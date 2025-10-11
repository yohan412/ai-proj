package com.example.CL.Project.attention;

import com.example.CL.Project.video.VideoChapter;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * 챕터별 평균 집중도 통계 Repository
 */
@Repository
public interface ChapterAttentionAvgRepository extends JpaRepository<ChapterAttentionAvg, Long> {
    
    /**
     * 특정 챕터의 평균 집중도 조회
     */
    Optional<ChapterAttentionAvg> findByChapter(VideoChapter chapter);
    
    /**
     * 여러 챕터의 평균 집중도 일괄 조회
     */
    List<ChapterAttentionAvg> findByChapterIn(List<VideoChapter> chapters);
}

