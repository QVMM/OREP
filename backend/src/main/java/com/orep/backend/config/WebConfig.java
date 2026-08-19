package com.orep.backend.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;

import java.nio.file.Paths;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Autowired
    private AuthInterceptor authInterceptor;

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(authInterceptor)
                .addPathPatterns(
                        "/api/**",
                        "/uploads/training/learning/**",
                        "/uploads/chat/**",
                        "/uploads/2024/**",
                        "/uploads/2025/**",
                        "/uploads/2026/**",
                        "/uploads/2027/**",
                        "/uploads/2028/**",
                        "/uploads/ai-score/**",
                        "/uploads/assistant/**",
                        "/uploads/resource-center/**",
                        "/uploads/office/versions/**",
                        "/uploads/course-videos/**",
                        "/uploads/course-attachments/**",
                        "/uploads/course-covers/**",
                        "/uploads/ppt-templates/**",
                        "/uploads/task/instructions/**"
                )
                .excludePathPatterns(
                        "/api/auth/login",
                        "/api/auth/register",
                        "/api/auth/send-code",
                        "/api/auth/check",
                        "/api/ai-score/callback",
                        "/api/ai-jury/personas",
                        "/api/ai-chat/callback",
                        "/api/recording/bot-complete",
                        "/api/recording/bot-failed",
                        "/api/ai-score/sessions/*/pipeline-callback",
                        "/api/assistant/internal/**",
                        // 启发 Office WOPI（Collabora 用 access_token，不走用户 Bearer）
                        "/api/wopi/**"
                );
    }

    @Bean
    public CorsFilter corsFilter() {
        CorsConfiguration config = new CorsConfiguration();
        config.addAllowedOriginPattern("*");
        config.addAllowedHeader("*");
        config.addAllowedMethod("*");
        config.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        String uploadLocation = Paths.get(uploadDir).toAbsolutePath().normalize().toUri().toString();
        registry.addResourceHandler("/uploads/**")
                .addResourceLocations(uploadLocation);
    }
}
