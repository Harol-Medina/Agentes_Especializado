package com.archaeologist;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class ArchaeologistApplication {

    public static void main(String[] args) {
        SpringApplication.run(ArchaeologistApplication.class, args);
    }
}
