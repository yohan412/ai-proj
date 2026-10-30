package com.example.CL.Project;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;

/**
 * Spring Boot Application
 * JPA 및 SQLite 사용
 */
@SpringBootApplication
@EnableJpaRepositories(basePackages = {
    "com.example.CL.Project.user", 
    "com.example.CL.Project.video",
    "com.example.CL.Project.attention"
})
public class ClProjectApplication {
    public static void main(String[] args) {
        new java.io.File("data").mkdirs();
        SpringApplication.run(ClProjectApplication.class, args);
    }
}
