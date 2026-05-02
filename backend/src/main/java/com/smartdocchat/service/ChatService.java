package com.smartdocchat.service;

import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.entity.Document;
import com.smartdocchat.repository.ChatMessageRepository;
import com.smartdocchat.repository.DocumentRepository;
import com.smartdocchat.util.GeminiConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class ChatService {
    private final ChatMessageRepository chatMessageRepository;
    private final DocumentRepository documentRepository;
    private final EmbeddingService embeddingService;
    private final GeminiConfig geminiConfig;

    private final RestTemplate restTemplate = new RestTemplate();

    private static final String GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models/";

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

        // Step 4: Call LLM (Gemini)
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
            String url = GEMINI_API_BASE + geminiConfig.getModel() + ":generateContent?key=" + geminiConfig.getApiKey();

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // Build Gemini request body
            Map<String, Object> textPart = new HashMap<>();
            textPart.put("text", prompt);

            Map<String, Object> systemPart = new HashMap<>();
            systemPart.put("text", "You are a helpful document assistant. Answer questions accurately based on the provided context.");

            Map<String, Object> systemContent = new HashMap<>();
            systemContent.put("role", "user");
            systemContent.put("parts", List.of(systemPart));

            Map<String, Object> userContent = new HashMap<>();
            userContent.put("role", "user");
            userContent.put("parts", List.of(textPart));

            Map<String, Object> generationConfig = new HashMap<>();
            generationConfig.put("temperature", geminiConfig.getTemperature());
            generationConfig.put("maxOutputTokens", 2048);

            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("contents", List.of(userContent));
            requestBody.put("generationConfig", generationConfig);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

            log.info("Calling Gemini API with model: {}", geminiConfig.getModel());

            ResponseEntity<Map> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    entity,
                    Map.class
            );

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                List<Map<String, Object>> candidates = (List<Map<String, Object>>) response.getBody().get("candidates");
                if (candidates != null && !candidates.isEmpty()) {
                    Map<String, Object> firstCandidate = candidates.get(0);
                    Map<String, Object> content = (Map<String, Object>) firstCandidate.get("content");
                    if (content != null) {
                        List<Map<String, Object>> parts = (List<Map<String, Object>>) content.get("parts");
                        if (parts != null && !parts.isEmpty()) {
                            return parts.get(0).get("text").toString();
                        }
                    }
                }
            }

            log.error("Gemini API returned unexpected response structure");
            return "Sorry, I could not generate a response. Please try again.";

        } catch (Exception e) {
            log.error("Error calling Gemini API: {}", e.getMessage(), e);
            return "Sorry, an error occurred while processing your question: " + e.getMessage();
        }
    }

    public void clearChatHistory(String sessionId) {
        List<ChatMessage> messages = getChatHistory(sessionId);
        chatMessageRepository.deleteAll(messages);
    }
}
