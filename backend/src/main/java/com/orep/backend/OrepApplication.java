package com.orep.backend;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@MapperScan("com.orep.backend.mapper")
@EnableScheduling
public class OrepApplication {
    public static void main(String[] args) {
        SpringApplication.run(OrepApplication.class, args);
    }
}
