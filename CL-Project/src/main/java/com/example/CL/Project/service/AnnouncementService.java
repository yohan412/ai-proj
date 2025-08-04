package com.example.CL.Project.service;

import com.example.CL.Project.domain.Announcement;
import com.example.CL.Project.dto.AnnouncementDto;
import com.example.CL.Project.repository.AnnouncementRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AnnouncementService {

    private final AnnouncementRepository announcementRepository;

    public List<AnnouncementDto> findAll() {
        return announcementRepository.findAll().stream()
                .map(this::toDto)
                .collect(Collectors.toList());
    }

    public AnnouncementDto findById(Long id) {
        return announcementRepository.findById(id)
                .map(this::toDto)
                .orElse(null);
    }

    @Transactional
    public AnnouncementDto save(AnnouncementDto dto) {
        Announcement announcement = Announcement.builder()
                .title(dto.getTitle())
                .writer(dto.getWriter())
                .password(dto.getPassword())
                .content(dto.getContent())
                .createdAt(LocalDateTime.now())
                .viewCount(0)
                .build();
        Announcement saved = announcementRepository.save(announcement);
        return toDto(saved);
    }

    @Transactional
    public void delete(Long id) {
        announcementRepository.deleteById(id);
    }

    @Transactional
    public AnnouncementDto update(Long id, AnnouncementDto dto) {
        Announcement announcement = announcementRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Invalid announcement Id:" + id));
        
        announcement.setTitle(dto.getTitle());
        announcement.setContent(dto.getContent());
        
        return toDto(announcement);
    }

    @Transactional
    public void increaseViewCount(Long id) {
        announcementRepository.findById(id).ifPresent(a -> a.setViewCount(a.getViewCount() + 1));
    }

    private AnnouncementDto toDto(Announcement announcement) {
        return AnnouncementDto.builder()
                .id(announcement.getId())
                .title(announcement.getTitle())
                .writer(announcement.getWriter())
                .content(announcement.getContent())
                .createdAt(announcement.getCreatedAt())
                .viewCount(announcement.getViewCount())
                .password(null) // Never expose password
                .build();
    }
}
