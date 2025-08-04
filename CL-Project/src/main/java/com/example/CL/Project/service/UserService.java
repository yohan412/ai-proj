package com.example.CL.Project.service;

import com.example.CL.Project.dto.UserDto;
import java.util.List;

public interface UserService {
    List<UserDto> getAllUsers();
    void grantRole(String username);
    void revokeRole(String username);
    boolean toggleUserAuthority(Long id);
}