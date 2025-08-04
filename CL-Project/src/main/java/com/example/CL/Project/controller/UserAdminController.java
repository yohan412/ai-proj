package com.example.CL.Project.controller;

import com.example.CL.Project.service.UserService;
import com.example.CL.Project.dto.UserDto;

import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import java.util.List;
@Controller
@RequestMapping("/admin/users")
public class UserAdminController {

    private final UserService userService;

    public UserAdminController(UserService userService) {
        this.userService = userService;
    }
 // 유저 리스트 출력
    @GetMapping
    public String userList(Model model) {
        List<UserDto> users = userService.getAllUsers();
        model.addAttribute("userList", users);
        return "user-control";
    }
 // 권한 토글 API (AJAX로 호출)
    @PostMapping("/{id}/toggle")
    @ResponseBody
    public ResponseEntity<?> toggleUserAuthority(@PathVariable Long id) {
        boolean updated = userService.toggleUserAuthority(id);
        return updated ? ResponseEntity.ok().build() : ResponseEntity.status(500).build();
    }
}