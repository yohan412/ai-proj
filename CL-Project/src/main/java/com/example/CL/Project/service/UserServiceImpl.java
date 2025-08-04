package com.example.CL.Project.service;

import com.example.CL.Project.domain.User;
import com.example.CL.Project.dto.UserDto;
import com.example.CL.Project.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class UserServiceImpl implements UserService {

    private final UserRepository userRepository;

    @Override
    public List<UserDto> getAllUsers() {
        return userRepository.findAll().stream()
                .map(this::toDto)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional
    public void grantRole(String username) {
        userRepository.findByUsername(username).ifPresent(user -> user.setRole("ROLE_ADMIN"));
    }

    @Override
    @Transactional
    public void revokeRole(String username) {
        userRepository.findByUsername(username).ifPresent(user -> user.setRole("ROLE_USER"));
    }

    @Override
    @Transactional
    public boolean toggleUserAuthority(Long id) {
        return userRepository.findById(id).map(user -> {
            if ("ROLE_USER".equals(user.getRole())) {
                user.setRole("ROLE_ADMIN");
            } else {
                user.setRole("ROLE_USER");
            }
            return true;
        }).orElse(false);
    }

    private UserDto toDto(User user) {
        return new UserDto(user.getId(), user.getUsername(), user.getEmail(), user.getRole());
    }
}
