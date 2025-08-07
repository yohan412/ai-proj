package com.example.CL.Project;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.hibernate.autoconfigure.HibernateJpaAutoConfiguration;
import org.springframework.boot.jdbc.autoconfigure.DataSourceAutoConfiguration;
//import org.springframework.context.annotation.Bean;
//import org.springframework.scheduling.annotation.EnableAsync;
//import org.springframework.scheduling.annotation.EnableScheduling;
//import org.springframework.web.client.RestTemplate;

//@SpringBootApplication
//@EnableScheduling
//@EnableAsync
@SpringBootApplication(exclude = {
	    DataSourceAutoConfiguration.class,
	    HibernateJpaAutoConfiguration.class
	})
public class ClProjectApplication {
    public static void main(String[] args) {
        SpringApplication.run(ClProjectApplication.class, args);
    }
//    @Bean
//    public RestTemplate restTemplate() {
//    return new RestTemplate();
//      }
 }

