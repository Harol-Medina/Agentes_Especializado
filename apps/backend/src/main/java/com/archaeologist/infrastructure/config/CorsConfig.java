package com.archaeologist.infrastructure.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Global CORS configuration for the Backend API.
 *
 * <p>In production, the nginx reverse proxy handles CORS. This configuration
 * enables direct access to the backend during local development (e.g., frontend
 * running on localhost:3000/3001 calling backend on localhost:8080).
 */
@Configuration
public class CorsConfig {

    @Bean
    public WebMvcConfigurer corsConfigurer() {
        return new WebMvcConfigurer() {
            @Override
            public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/api/**")
                    .allowedOrigins(
                        "http://localhost:3000",
                        "http://localhost:3001",
                        "http://localhost:80",
                        "http://localhost"
                    )
                    .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                    .allowedHeaders("*")
                    .allowCredentials(true)
                    .maxAge(3600);

                registry.addMapping("/actuator/**")
                    .allowedOrigins("*")
                    .allowedMethods("GET");
            }
        };
    }
}
