package com.smartdocchat.service;

import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.repository.ChatMessageRepository;
import com.smartdocchat.util.OpenAIConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class ChatService {
    private final ChatMessageRepository chatMessageRepository;
    private final EmbeddingService embeddingService;
    private final OpenAIConfig openAIConfig;

    public ChatMessage processQuery(String sessionId, Long documentId, String userMessage) {
        // Step 1: Search for relevant chunks
        List<String> relevantChunks = embeddingService.semanticSearch(userMessage, documentId);
        String sourceChunks = String.join("\n---\n", relevantChunks);

        // Step 2: Build prompt with context
        String prompt = buildPrompt(userMessage, relevantChunks);

        // Step 3: Call LLM (OpenAI in this case)
        String aiResponse = callLLM(prompt);

        // Step 4: Save to database
        ChatMessage chatMessage = ChatMessage.builder()
                .sessionId(sessionId)
                .documentId(documentId)
                .userMessage(userMessage)
                .aiResponse(aiResponse)
                .sourceChunks(sourceChunks)
                .build();

        return chatMessageRepository.save(chatMessage);
    }

    public List<ChatMessage> getChatHistory(String sessionId) {
        return chatMessageRepository.findBySessionIdOrderByCreatedAtAsc(sessionId);
    }

    public List<ChatMessage> getChatHistory(String sessionId, Long documentId) {
        return chatMessageRepository.findBySessionIdAndDocumentIdOrderByCreatedAtAsc(sessionId, documentId);
    }

    private String buildPrompt(String userQuestion, List<String> relevantChunks) {
        StringBuilder prompt = new StringBuilder();
        prompt.append("You are a helpful assistant. Use the following context to answer the user's question.\n\n");
        prompt.append("Context:\n");
        for (String chunk : relevantChunks) {
            prompt.append("- ").append(chunk).append("\n");
        }
        prompt.append("\nUser Question: ").append(userQuestion);
        prompt.append("\n\nAnswer:");
        return prompt.toString();
    }

    private String callLLM(String prompt) {
        // Integration with OpenAI API (placeholder)
        log.info("Calling LLM with prompt of length: {}", prompt.length());
        // In production, use OpenAI client to generate response
        return "This is a placeholder response. In production, this would call OpenAI API.";
    }

    public void clearChatHistory(String sessionId) {
        List<ChatMessage> messages = getChatHistory(sessionId);
        chatMessageRepository.deleteAll(messages);
    }
}
