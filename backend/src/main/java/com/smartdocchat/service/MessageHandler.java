package com.smartdocchat.service;

import com.smartdocchat.util.LlmConfig;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.Consumer;

@Service
@RequiredArgsConstructor
@Slf4j
public class MessageHandler {

    private final LlmConfig llmConfig;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public String buildPrompt(String userQuestion, List<String> relevantChunks) {
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

    public String callLLM(String prompt) {
        String result = null;
        int maxAttempts = llmConfig.getMaxAttempts();
        long backoff = llmConfig.getRetryBackoffMs();

        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            result = callLLMOnce(prompt);
            if (!result.startsWith("Sorry, the language model is temporarily unavailable.")
                    && !result.startsWith("Sorry, I could not generate a response.")) {
                return result;
            }
            if (attempt < maxAttempts) {
                try {
                    Thread.sleep(backoff * attempt);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    return result;
                }
            }
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    public String callLLMOnce(String prompt) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(buildChatRequest(prompt, false), headers);
            log.info("Calling local LLM model: {}", llmConfig.getChatModel());

            ResponseEntity<Map> response = restTemplate.exchange(
                    llmConfig.getChatUrl(),
                    HttpMethod.POST,
                    entity,
                    Map.class
            );

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                Map<String, String> message = (Map<String, String>) response.getBody().get("message");
                if (message != null && message.get("content") != null) {
                    return message.get("content");
                }
            }

            log.error("LLM API returned unexpected response structure");
            return "Sorry, I could not generate a response. Please try again.";

        } catch (Exception e) {
            log.error("Error calling LLM API: {}", e.getMessage(), e);
            return "Sorry, the language model is temporarily unavailable. Please try again.";
        }
    }

    public void streamLLM(String prompt, Consumer<String> onToken) {
        restTemplate.execute(llmConfig.getChatUrl(), HttpMethod.POST, request -> {
            request.getHeaders().setContentType(MediaType.APPLICATION_JSON);
            objectMapper.writeValue(request.getBody(), buildChatRequest(prompt, true));
        }, response -> {
            if (!response.getStatusCode().is2xxSuccessful()) {
                throw new IllegalStateException("Ollama stream request failed: " + response.getStatusCode());
            }
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(response.getBody(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    JsonNode message = objectMapper.readTree(line).path("message");
                    String token = message.path("content").asText("");
                    if (!token.isEmpty()) {
                        onToken.accept(token);
                    }
                }
            }
            return null;
        });
    }

    private Map<String, Object> buildChatRequest(String prompt, boolean stream) {
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("model", llmConfig.getChatModel());
        requestBody.put("messages", List.of(
                Map.of("role", "system",
                        "content", "You are a helpful document assistant. Answer questions accurately based on the provided context."),
                Map.of("role", "user", "content", prompt)));
        requestBody.put("options",
                Map.of("temperature", llmConfig.getTemperature(), "num_predict", 2048));
        requestBody.put("stream", stream);
        return requestBody;
    }
}