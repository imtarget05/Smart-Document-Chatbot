package com.smartdocchat.service;

import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.entity.Document;
import com.smartdocchat.repository.ChatMessageRepository;
import com.smartdocchat.repository.DocumentRepository;
import com.smartdocchat.util.OpenRouterConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class ChatService {
    private final ChatMessageRepository chatMessageRepository;
    private final DocumentRepository documentRepository;
    private final EmbeddingService embeddingService;
    private final OpenRouterConfig openRouterConfig;

    private final RestTemplate restTemplate = new RestTemplate();

    private static final String OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions";

    public ChatMessage processQuery(String sessionId, Long documentId, String userMessage) {
        // Step 1: Find document and get vectorCollectionId
        String vectorCollectionId = null;
        if (documentId != null) {
            Optional<Document> docOpt = documentRepository.findById(documentId);
            if (docOpt.isPresent()) {
                vectorCollectionId = docOpt.get().getVectorCollectionId();
            }
        }

        // Step 2: Search for relevant chunks using vectorCollectionId
        List<String> relevantChunks;
        if (vectorCollectionId != null && !vectorCollectionId.isBlank()) {
            relevantChunks = embeddingService.semanticSearchByCollection(userMessage, vectorCollectionId);
        } else {
            relevantChunks = Collections.emptyList();
        }
        String sourceChunks = String.join("\n---\n", relevantChunks);

        // Step 3: Build prompt with context
        String prompt = buildPrompt(userMessage, relevantChunks);

        // Step 4: Call LLM (OpenRouter)
        String aiResponse = callLLM(prompt);

        // Step 5: Save to database
        ChatMessage chatMessage = ChatMessage.builder()
                .sessionId(sessionId)
                .documentId(documentId)
                .userMessage(userMessage)
                .aiResponse(aiResponse)
                .sourceChunks(sourceChunks.isEmpty() ? null : sourceChunks)
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
        prompt.append("You are a helpful assistant that answers questions based on the provided document context. ");
        prompt.append("If the context is empty or does not contain relevant information, acknowledge that and answer based on your general knowledge.\n\n");

        if (!relevantChunks.isEmpty()) {
            prompt.append("Context from the document:\n");
            for (int i = 0; i < relevantChunks.size(); i++) {
                prompt.append("[").append(i + 1).append("] ").append(relevantChunks.get(i)).append("\n\n");
            }
        } else {
            prompt.append("No relevant context was found in the document.\n\n");
        }

        prompt.append("User Question: ").append(userQuestion);
        return prompt.toString();
    }

    @SuppressWarnings("unchecked")
    private String callLLM(String prompt) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setBearerAuth(openRouterConfig.getApiKey());

            List<Map<String, String>> messages = new ArrayList<>();
            messages.add(Map.of(
                    "role", "system",
                    "content", "You are a helpful document assistant. Answer questions accurately based on the provided context."
            ));
            messages.add(Map.of(
                    "role", "user",
                    "content", prompt
            ));

            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("model", openRouterConfig.getModel());
            requestBody.put("messages", messages);
            requestBody.put("temperature", openRouterConfig.getTemperature());
            requestBody.put("max_tokens", 2048);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            log.info("Calling OpenRouter API with model: {}", openRouterConfig.getModel());

            ResponseEntity<Map> response = restTemplate.exchange(
                    OPENROUTER_CHAT_URL,
                    HttpMethod.POST,
                    entity,
                    Map.class
            );

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                List<Map<String, Object>> choices = (List<Map<String, Object>>) response.getBody().get("choices");
                if (choices != null && !choices.isEmpty()) {
                    Map<String, Object> firstChoice = choices.get(0);
                    Map<String, String> message = (Map<String, String>) firstChoice.get("message");
                    if (message != null) {
                        return message.get("content");
                    }
                }
            }

            log.error("OpenRouter API returned unexpected response structure");
            return "Sorry, I could not generate a response. Please try again.";

        } catch (Exception e) {
            log.error("Error calling OpenRouter API: {}", e.getMessage(), e);
            return "Sorry, an error occurred while processing your question: " + e.getMessage();
        }
    }

    public void clearChatHistory(String sessionId) {
        List<ChatMessage> messages = getChatHistory(sessionId);
        chatMessageRepository.deleteAll(messages);
    }
}
