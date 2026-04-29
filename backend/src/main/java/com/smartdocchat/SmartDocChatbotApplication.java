package com.smartdocchat;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

@SpringBootApplication
public class SmartDocChatbotApplication {

    public static void main(String[] args) {
        SpringApplication.run(SmartDocChatbotApplication.class, args);
    }

    @Configuration
    @EnableWebSocketMessageBroker
    public static class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

        @Override
        public void configureMessageBroker(MessageBrokerRegistry config) {
            config.enableSimpleBroker("/topic", "/user");
            config.setApplicationDestinationPrefixes("/app");
            config.setUserDestinationPrefix("/user");
        }

        @Override
        public void registerStompEndpoints(StompEndpointRegistry registry) {
            registry.addEndpoint("/ws/chat")
                    .setAllowedOrigins("http://localhost:3000", "http://localhost:8080")
                    .withSockJS();
        }
    }
}
