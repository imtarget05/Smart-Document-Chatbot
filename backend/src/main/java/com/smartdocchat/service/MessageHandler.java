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
    private final com.smartdocchat.metrics.RagMetrics ragMetrics;
    private final LlmClient llmClient;
    private final ObjectMapper objectMapper = new ObjectMapper();
    @org.springframework.beans.factory.annotation.Value("${security.internal-token:}")
    private String internalToken;


    private static final String DEFAULT_SYSTEM_PROMPT =
            "You are a helpful document assistant. Answer questions accurately based on the provided context.";

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

    /** Prompt for the deep-reasoning fallback: no document context is available. */
    public String buildGeneralKnowledgePrompt(String userQuestion) {
        return "The retrieved documents do not contain enough relevant information. "
                + "Use your internal knowledge to answer as accurately as possible.\n\n"
                + "User Question: " + userQuestion;
    }

    /** Prompt for the web-search fallback: answers grounded in the returned snippets. */
    public String buildWebSearchPrompt(String userQuestion, List<String> snippets) {
        StringBuilder prompt = new StringBuilder();
        prompt.append("Based on the following web search results, answer the question. ")
                .append("Include the source context where relevant.\n\nWeb search results:\n");
        for (int i = 0; i < snippets.size(); i++) {
            prompt.append("[").append(i + 1).append("] ").append(snippets.get(i)).append("\n\n");
        }
        prompt.append("User Question: ").append(userQuestion);
        return prompt.toString();
    }

    /**
     * Safe abstention response for unanswerable questions: no sufficient
     * evidence was retrieved and no fallback was available, so the system
     * refuses to fabricate an answer.
     */
    public String buildAbstentionResponse() {
        return "I couldn't find sufficient evidence in the provided documents to answer this question. "
                + "Please rephrase the question or upload a document that covers this topic.";
    }

    /** Response when a user message is rejected as a prompt-injection attempt. */
    public String buildInjectionBlockedResponse() {
        return "I can't process this request: it appears to contain instructions that attempt to "
                + "override the assistant's behavior. Please rephrase your question in a normal way.";
    }

    // ------------------------------------------------------------------
    // LLM calls
    // ------------------------------------------------------------------

    public String callLLM(String prompt) {
        return callLLM(DEFAULT_SYSTEM_PROMPT, prompt);
    }

    public String callLLM(String systemPrompt, String userPrompt) {
        String result = null;
        int maxAttempts = llmConfig.getMaxAttempts();
        long backoff = llmConfig.getRetryBackoffMs();

        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            // Each attempt goes through the circuit-breaker-guarded client;
            // when the breaker is open the attempts fail fast instead of
            // hammering a struggling provider.
            result = callLLMOnce(systemPrompt, userPrompt);
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
        return callLLMOnce(DEFAULT_SYSTEM_PROMPT, prompt);
    }

    public String callLLMOnce(String systemPrompt, String userPrompt) {
        return llmClient.chat(systemPrompt, userPrompt);
    }

    public void streamLLM(String prompt, Consumer<String> onToken) {
        streamLLM(DEFAULT_SYSTEM_PROMPT, prompt, onToken);
    }

    public void streamLLM(String systemPrompt, String userPrompt, Consumer<String> onToken) {
        restTemplate.execute(llmConfig.getChatUrl(), HttpMethod.POST, request -> {
            request.getHeaders().setContentType(MediaType.APPLICATION_JSON);
            if (internalToken != null && !internalToken.isBlank()) {
                request.getHeaders().set("X-Internal-Token", internalToken);
            }
            objectMapper.writeValue(request.getBody(), buildChatRequest(systemPrompt, userPrompt, true));
        }, response -> {
            if (!response.getStatusCode().is2xxSuccessful()) {
                throw new IllegalStateException("LLM stream request failed: " + response.getStatusCode());
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

    private Map<String, Object> buildChatRequest(String systemPrompt, String userPrompt, boolean stream) {
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("model", llmConfig.getChatModel());
        requestBody.put("messages", List.of(
                Map.of("role", "system", "content", systemPrompt),
                Map.of("role", "user", "content", userPrompt)));
        requestBody.put("options",
                Map.of("temperature", llmConfig.getTemperature(), "top_p", llmConfig.getTopP(), "num_predict", 2048));
        requestBody.put("stream", stream);
        return requestBody;
    }
}