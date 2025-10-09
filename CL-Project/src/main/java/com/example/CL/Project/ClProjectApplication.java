package com.example.CL.Project;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;

/**
 * Spring Boot Application
 * JPA 및 Oracle Database 사용
 */
@SpringBootApplication
@EnableJpaRepositories(basePackages = {"com.example.CL.Project.user", "com.example.CL.Project.video"})
public class ClProjectApplication {
    public static void main(String[] args) {
        SpringApplication.run(ClProjectApplication.class, args);
    }
}
