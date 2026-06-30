package com.smartdocchat.service;

import com.smartdocchat.dto.RetrievedChunk;
import com.smartdocchat.util.LlmConfig;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.Consumer;

/**
 * MessageHandler — Single Responsibility: transform, validate, and format
 * all message content (prompts, query reformulation, LLM calls, web search).
 *
 * Does NOT persist anything; purely stateless input/output transformation.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class MessageHandler {

    private final LlmConfig llmConfig;
    private final RestTemplate restTemplate;
    private final RagMetrics ragMetrics;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${tavily.api.key:}")
    private String tavilyApiKey;

    // -----------------------------------------------------------------------
    // Prompt construction
    // -----------------------------------------------------------------------

    /**
     * Build a RAG prompt from the user question and a list of context chunks.
     */
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

    // -----------------------------------------------------------------------
    // Query reformulation (Agentic CRAG Step 1)
    // -----------------------------------------------------------------------

    /**
     * Ask the LLM to produce 2 alternative search-optimised query variations.
     */
    public List<String> reformulateQuery(String userMessage) {
        String reformulatePrompt = "You are a query reformulation agent. Your task is to rewrite the user's query into 2 search-optimized variations "
                + "to improve retrieval in a vector database. Write exactly two variations, one per line, and absolutely nothing else. "
                + "Do not write any introductory or concluding text, and do not use bullet points or numbering. Just write the two variations. "
                + "Here is the user query: \"" + userMessage + "\"";

        String response = callLLM(reformulatePrompt);

        // Strip <think> tags (DeepSeek / chain-of-thought models)
        if (response.contains("</think>")) {
            response = response.substring(response.lastIndexOf("</think>") + 8).trim();
        }

        List<String> variations = new ArrayList<>();
        String[] lines = response.split("\n");
        for (String line : lines) {
            String cleanLine = line.replaceAll("^[\\-\\d\\.\\*\\s\\🤖]+", "").trim();
            if (!cleanLine.isEmpty() && variations.size() < 2) {
                variations.add(cleanLine);
            }
        }

        // Fallback if parsing failed
        if (variations.isEmpty()) {
            variations.add(userMessage + " overview");
            variations.add(userMessage + " details");
        } else if (variations.size() == 1) {
            variations.add(variations.get(0) + " overview");
        }

        log.info("Agentic Query Reformulation variations: {}", variations);
        return variations;
    }

    // -----------------------------------------------------------------------
    // LLM calling (with retry)
    // -----------------------------------------------------------------------

    /**
     * Call the LLM with automatic retry on transient failures.
     */
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

    /**
     * Single (non-retried) LLM call, returns a raw content string.
     */
    @SuppressWarnings("unchecked")
    public String callLLMOnce(String prompt) {
        long startTime = System.currentTimeMillis();
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
                    ragMetrics.llmLatency(System.currentTimeMillis() - startTime, "success");
                    return message.get("content");
                }
            }

            log.error("LLM API returned unexpected response structure");
            ragMetrics.llmLatency(System.currentTimeMillis() - startTime, "invalid_response");
            return "Sorry, I could not generate a response. Please try again.";

        } catch (Exception e) {
            log.error("Error calling LLM API: {}", e.getMessage(), e);
            ragMetrics.llmLatency(System.currentTimeMillis() - startTime, "failure");
            return "Sorry, the language model is temporarily unavailable. Please try again.";
        }
    }

    /**
     * Stream LLM tokens; each token is delivered to the provided {@code onToken} consumer.
     */
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

    // -----------------------------------------------------------------------
    // Web search fallback
    // -----------------------------------------------------------------------

    /**
     * Call the Tavily Search API. Returns empty list if key is not configured.
     */
    @SuppressWarnings("unchecked")
    public List<String> searchWeb(String query) {
        if (tavilyApiKey == null || tavilyApiKey.isBlank()
                || tavilyApiKey.equals("your-tavily-api-key-here")) {
            log.info("Tavily API Key is not set or empty. Skipping web search fallback.");
            return Collections.emptyList();
        }

        try {
            String url = "https://api.tavily.com/search";
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, Object> body = new HashMap<>();
            body.put("api_key", tavilyApiKey);
            body.put("query", query);
            body.put("search_depth", "basic");
            body.put("max_results", 3);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            log.info("Invoking Tavily Web Search for query: '{}'", query);

            ResponseEntity<Map> response = restTemplate.exchange(url, HttpMethod.POST, entity, Map.class);

            List<String> webContexts = new ArrayList<>();
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                List<Map<String, Object>> results =
                        (List<Map<String, Object>>) response.getBody().get("results");
                if (results != null) {
                    for (Map<String, Object> result : results) {
                        String title = (String) result.get("title");
                        String content = (String) result.get("content");
                        String resultUrl = (String) result.get("url");
                        webContexts.add("[Web Search: " + title + " (" + resultUrl + ")] " + content);
                    }
                }
            }
            log.info("Tavily Web Search retrieved {} results.", webContexts.size());
            return webContexts;
        } catch (Exception e) {
            log.error("Error calling Tavily Web Search API: {}", e.getMessage(), e);
            return Collections.emptyList();
        }
    }

    // -----------------------------------------------------------------------
    // Internal helpers
    // -----------------------------------------------------------------------

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
