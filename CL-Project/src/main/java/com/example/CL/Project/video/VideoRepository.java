package com.example.CL.Project.video;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface VideoRepository extends JpaRepository<Video, Long> {
    Optional<Video> findByStoredName(String storedName);
    boolean existsByStoredName(String storedName);
}

