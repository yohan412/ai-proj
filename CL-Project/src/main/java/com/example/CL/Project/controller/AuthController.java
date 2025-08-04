package com.example.CL.Project.controller;

import com.example.CL.Project.domain.User;
import com.example.CL.Project.dto.LoginRequest;
import com.example.CL.Project.dto.RegisterRequest;
import com.example.CL.Project.repository.UserRepository;
import com.example.CL.Project.dto.JwtAuthResponse;
import com.example.CL.Project.service.FileService;
import com.example.CL.Project.service.JwtTokenProvider;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthenticationManager authenticationManager;
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider tokenProvider;
    private final RedisTemplate<String, String> redisTemplate;
    private final FileService fileService;

    public AuthController(AuthenticationManager authenticationManager, UserRepository userRepository, PasswordEncoder passwordEncoder, JwtTokenProvider tokenProvider, RedisTemplate<String, String> redisTemplate, FileService fileService) {
        this.authenticationManager = authenticationManager;
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.tokenProvider = tokenProvider;
        this.redisTemplate = redisTemplate;
        this.fileService = fileService;
    }

    @PostMapping("/register")
    public ResponseEntity<?> registerUser(@RequestBody RegisterRequest registerRequest) {
        if (userRepository.findByUsername(registerRequest.getUsername()).isPresent()) {
            return ResponseEntity.badRequest().body("Error: Username is already taken!");
        }

        // Add a check for email as well
        // if (userRepository.findByEmail(registerRequest.getEmail()).isPresent()) {
        //     return ResponseEntity.badRequest().body("Error: Email is already in use!");
        // }

        User user = new User();
        user.setUsername(registerRequest.getUsername());
        user.setEmail(registerRequest.getEmail());
        user.setPassword(passwordEncoder.encode(registerRequest.getPassword()));
        user.setRole("ROLE_USER"); // Assign default role

        userRepository.save(user);

        return ResponseEntity.ok("User registered successfully!");
    }

    @PostMapping("/login")
    public ResponseEntity<?> authenticateUser(@RequestBody LoginRequest loginRequest) {
        System.out.println("--- AuthController: /login endpoint hit ---");
        System.out.println("Attempting to authenticate user: " + loginRequest.getUsername());

        Authentication authentication = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(loginRequest.getUsername(), loginRequest.getPassword()));
        
        System.out.println("User authenticated successfully!");

        SecurityContextHolder.getContext().setAuthentication(authentication);

        String jwt = tokenProvider.generateToken(authentication);
        System.out.println("Generated JWT: " + jwt);

        JwtAuthResponse response = new JwtAuthResponse(jwt);
        System.out.println("Returning response with token.");
        
        return ResponseEntity.ok(response);
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logoutUser() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.getPrincipal() instanceof UserDetails) {
            UserDetails userDetails = (UserDetails) authentication.getPrincipal();
            String username = userDetails.getUsername();

            // 1. Delete the JWT key from Redis. This invalidates the session on the server.
            redisTemplate.delete("jwt:" + username);
            System.out.println("Manually deleted JWT from Redis for user: " + username);

            // 2. Immediately delete user files. This is crucial because a manual delete
            // does not trigger the Redis expiration listener.
            fileService.deleteUserFiles(username);

            return ResponseEntity.ok("User logged out successfully and files cleaned up.");
        }
        return ResponseEntity.badRequest().body("No user is currently authenticated.");
    }
}
