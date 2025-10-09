package com.example.CL.Project.video;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface VideoChapterRepository extends JpaRepository<VideoChapter, Long> {
    List<VideoChapter> findByStoredNameOrderByStartTimeAsc(String storedName);
    void deleteByStoredName(String storedName);
}

