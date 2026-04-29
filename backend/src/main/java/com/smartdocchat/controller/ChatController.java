package com.smartdocchat.controller;

import com.smartdocchat.dto.ChatRequest;
import com.smartdocchat.dto.ChatResponse;
import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.service.ChatService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/chat")
@RequiredArgsConstructor
@Slf4j
public class ChatController {
    private final ChatService chatService;

    @PostMapping("/ask")
    public ResponseEntity<ChatResponse> askQuestion(@RequestBody ChatRequest request) {
        try {
            ChatMessage message = chatService.processQuery(
                    request.getSessionId(),
                    request.getDocumentId(),
                    request.getMessage()
            );
            return ResponseEntity.ok(convertToResponse(message));
        } catch (Exception e) {
            log.error("Error processing chat request", e);
            return ResponseEntity.status(500).build();
        }
    }

    @GetMapping("/history/{sessionId}")
    public ResponseEntity<List<ChatResponse>> getChatHistory(@PathVariable String sessionId) {
        List<ChatMessage> messages = chatService.getChatHistory(sessionId);
        List<ChatResponse> responses = messages.stream()
                .map(this::convertToResponse)
                .collect(Collectors.toList());
        return ResponseEntity.ok(responses);
    }

    @GetMapping("/history/{sessionId}/{documentId}")
    public ResponseEntity<List<ChatResponse>> getChatHistory(
            @PathVariable String sessionId,
            @PathVariable Long documentId) {
        List<ChatMessage> messages = chatService.getChatHistory(sessionId, documentId);
        List<ChatResponse> responses = messages.stream()
                .map(this::convertToResponse)
                .collect(Collectors.toList());
        return ResponseEntity.ok(responses);
    }

    @DeleteMapping("/history/{sessionId}")
    public ResponseEntity<String> clearChatHistory(@PathVariable String sessionId) {
        chatService.clearChatHistory(sessionId);
        return ResponseEntity.ok("Chat history cleared");
    }

    // WebSocket endpoint for real-time chat
    @MessageMapping("/chat/send")
    @SendTo("/topic/messages")
    public ChatResponse handleChatMessage(ChatRequest request) {
        log.info("Processing message from session: {}", request.getSessionId());
        ChatMessage message = chatService.processQuery(
                request.getSessionId(),
                request.getDocumentId(),
                request.getMessage()
        );
        return convertToResponse(message);
    }

    private ChatResponse convertToResponse(ChatMessage message) {
        return ChatResponse.builder()
                .id(message.getId())
                .sessionId(message.getSessionId())
                .userMessage(message.getUserMessage())
                .aiResponse(message.getAiResponse())
                .sourceChunks(message.getSourceChunks())
                .documentId(message.getDocumentId())
                .build();
    }
}
