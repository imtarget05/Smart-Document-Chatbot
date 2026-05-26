package com.smartdocchat.service;

import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.entity.Document;
import com.smartdocchat.repository.ChatMessageRepository;
import com.smartdocchat.repository.DocumentRepository;
import com.smartdocchat.util.OllamaConfig;
import com.smartdocchat.dto.RetrievedChunk;
import com.smartdocchat.dto.ChatResponse;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

@Service
@RequiredArgsConstructor
@Slf4j
public class ChatService {
    private final ChatMessageRepository chatMessageRepository;
    private final DocumentRepository documentRepository;
    private final EmbeddingService embeddingService;
    private final OllamaConfig ollamaConfig;
    private final RestTemplate restTemplate;
    private final RagMetrics ragMetrics;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${tavily.api.key:}")
    private String tavilyApiKey;

    @Value("${llm.max-attempts:3}")
    private int llmMaxAttempts;

    @Value("${llm.retry-backoff-ms:250}")
    private long llmRetryBackoffMs;

    public ChatMessage processQuery(String ownerUsername, String sessionId, Long documentId, List<Long> documentIds,
                                    String userMessage) {
        ragMetrics.request("sync");
        List<Long> finalDocIds = new ArrayList<>();
        if (documentIds != null && !documentIds.isEmpty()) {
            finalDocIds.addAll(documentIds);
        } else if (documentId != null) {
            finalDocIds.add(documentId);
        }

        double initialMaxScore = 0.0;
        List<RetrievedChunk> initialChunks = new ArrayList<>();
        Map<RetrievedChunk, String> initialChunkToFileNameMap = new HashMap<>();

        // 1. Initial Retrieval
        for (Long docId : finalDocIds) {
            Optional<Document> docOpt = documentRepository.findByIdAndOwnerUsername(docId, ownerUsername);
            if (docOpt.isPresent()) {
                Document doc = docOpt.get();
                String vectorCollectionId = doc.getVectorCollectionId();
                if (vectorCollectionId != null && !vectorCollectionId.isBlank()) {
                    List<RetrievedChunk> chunks = embeddingService.searchChunks(userMessage, vectorCollectionId, 3);
                    for (RetrievedChunk chunk : chunks) {
                        initialChunks.add(chunk);
                        initialChunkToFileNameMap.put(chunk, doc.getFileName());
                        if (chunk.getScore() > initialMaxScore) {
                            initialMaxScore = chunk.getScore();
                        }
                    }
                }
            }
        }

        String aiResponse = "";
        String sourceChunks = "";
        double finalMaxScore = initialMaxScore;
        ragMetrics.confidence(initialMaxScore);

        if (initialMaxScore >= 0.45) {
            // Standard RAG flow: High Confidence
            List<String> contextList = new ArrayList<>();
            for (RetrievedChunk chunk : initialChunks) {
                String fileName = initialChunkToFileNameMap.get(chunk);
                contextList.add("[" + fileName + "] " + chunk.getParentText());
            }
            sourceChunks = String.join("\n---\n", contextList);
            String prompt = buildPrompt(userMessage, contextList);

            long startTime = System.currentTimeMillis();
            aiResponse = callLLM(prompt);
            long latencyMs = System.currentTimeMillis() - startTime;
            logToMLflow(userMessage, aiResponse, latencyMs);
        } else {
            ragMetrics.fallback("corrective_retrieval");
            // Agentic CRAG Loop: Low Confidence (< 0.45)
            log.info("RAG confidence is low ({} < 0.45). Activating Agentic Loop...", initialMaxScore);

            // Step 1: Query Reformulation via DeepSeek R1
            List<String> queryVariations = reformulateQuery(userMessage);
            List<String> allQueries = new ArrayList<>();
            allQueries.add(userMessage);
            allQueries.addAll(queryVariations);

            // Step 2: Parallel Re-retrieval
            List<CompletableFuture<Void>> futures = new ArrayList<>();
            List<RetrievedChunk> agentChunks = Collections.synchronizedList(new ArrayList<>());
            Map<RetrievedChunk, String> agentChunkToFileNameMap = Collections.synchronizedMap(new HashMap<>());

            for (String q : allQueries) {
                for (Long docId : finalDocIds) {
                    Optional<Document> docOpt = documentRepository.findByIdAndOwnerUsername(docId, ownerUsername);
                    if (docOpt.isPresent()) {
                        Document doc = docOpt.get();
                        String vectorCollectionId = doc.getVectorCollectionId();
                        if (vectorCollectionId != null && !vectorCollectionId.isBlank()) {
                            futures.add(CompletableFuture.runAsync(() -> {
                                List<RetrievedChunk> chunks = embeddingService.searchChunks(q, vectorCollectionId, 3);
                                for (RetrievedChunk chunk : chunks) {
                                    agentChunks.add(chunk);
                                    agentChunkToFileNameMap.put(chunk, doc.getFileName());
                                }
                            }));
                        }
                    }
                }
            }

            // Wait for parallel retrievals to complete
            CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();

            // Step 3: Deduplicate & Rerank
            Map<String, RetrievedChunk> uniqueChunks = new HashMap<>();
            for (RetrievedChunk chunk : agentChunks) {
                String text = chunk.getText().trim();
                if (!uniqueChunks.containsKey(text) || uniqueChunks.get(text).getScore() < chunk.getScore()) {
                    uniqueChunks.put(text, chunk);
                }
            }

            List<RetrievedChunk> rerankedChunks = new ArrayList<>(uniqueChunks.values());
            rerankedChunks.sort((a, b) -> Double.compare(b.getScore(), a.getScore()));

            double agenticMaxScore = 0.0;
            if (!rerankedChunks.isEmpty()) {
                agenticMaxScore = rerankedChunks.get(0).getScore();
            }
            finalMaxScore = agenticMaxScore;

            long startTime = System.currentTimeMillis();
            if (agenticMaxScore >= 0.45) {
                // Agentic Synthesis (Confidence successfully restored!)
                List<RetrievedChunk> topChunks = rerankedChunks.subList(0, Math.min(rerankedChunks.size(), 4));
                List<String> contextList = new ArrayList<>();
                for (RetrievedChunk chunk : topChunks) {
                    String fileName = agentChunkToFileNameMap.get(chunk);
                    contextList.add("[" + fileName + "] " + chunk.getParentText());
                }
                sourceChunks = String.join("\n---\n", contextList);
                String prompt = buildPrompt(userMessage, contextList);

                String llmAnswer = callLLM(prompt);
                aiResponse = "🤖 [Agentic Workflow Activated: Query Reformulation & Parallel retrieval executed because initial RAG confidence was "
                        + String.format(Locale.US, "%.1f", initialMaxScore * 100) + "%]\n\n" + llmAnswer;
            } else {
                // Deep Reasoning Fallback with Web Search mitigation
                log.info("Agentic re-retrieval yielded low score ({} < 0.45). Attempting Web Search Fallback...", agenticMaxScore);
                List<String> webContexts = searchWeb(userMessage);

                if (!webContexts.isEmpty()) {
                    ragMetrics.fallback("web_search");
                    sourceChunks = String.join("\n---\n", webContexts);
                    String prompt = buildPrompt(userMessage, webContexts);
                    String llmAnswer = callLLM(prompt);
                    aiResponse = "🌐 [Độ tin cậy tài liệu thấp. Đang bổ sung ngữ cảnh trực tuyến từ Web Search...]\n\n" + llmAnswer;
                } else {
                    ragMetrics.fallback("general_knowledge");
                    String fallbackPrompt = "The user is asking a question that is NOT covered by the loaded documents (retrieval confidence is too low, max score: "
                            + agenticMaxScore + "). Please use your deep reasoning, internal knowledge, and general knowledge to answer the question as comprehensively and accurately as possible.\n\n"
                            + "User Question: " + userMessage;

                    String llmAnswer = callLLM(fallbackPrompt);
                    aiResponse = "⚠️ Độ tin cậy thấp (RAG Confidence < 45%). Đang kích hoạt chế độ Suy Luận Sâu của Agent...\n\n" + llmAnswer;
                }
            }
            long latencyMs = System.currentTimeMillis() - startTime;
            logToMLflow(userMessage, aiResponse, latencyMs);
        }

        // Convert document IDs to comma-separated string for DB
        String docIdsStr = null;
        if (!finalDocIds.isEmpty()) {
            List<String> strIds = new ArrayList<>();
            for (Long id : finalDocIds) {
                strIds.add(id.toString());
            }
            docIdsStr = String.join(",", strIds);
        }

        // Save to database
        ChatMessage chatMessage = ChatMessage.builder()
                .sessionId(sessionId)
                .ownerUsername(ownerUsername)
                .documentId(documentId != null ? documentId : (finalDocIds.isEmpty() ? null : finalDocIds.get(0)))
                .documentIds(docIdsStr)
                .userMessage(userMessage)
                .aiResponse(aiResponse)
                .sourceChunks(sourceChunks.isEmpty() ? null : sourceChunks)
                .build();

        return chatMessageRepository.save(chatMessage);
    }

    private List<String> reformulateQuery(String userMessage) {
        String reformulatePrompt = "You are a query reformulation agent. Your task is to rewrite the user's query into 2 search-optimized variations "
                + "to improve retrieval in a vector database. Write exactly two variations, one per line, and absolutely nothing else. "
                + "Do not write any introductory or concluding text, and do not use bullet points or numbering. Just write the two variations. "
                + "Here is the user query: \"" + userMessage + "\"";

        String response = callLLM(reformulatePrompt);

        // Parse variations, clean up <think> tags if any
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

        // Fallback variations if parsing failed or returned too few
        if (variations.isEmpty()) {
            variations.add(userMessage + " overview");
            variations.add(userMessage + " details");
        } else if (variations.size() == 1) {
            variations.add(variations.get(0) + " overview");
        }

        log.info("Agentic Query Reformulation variations: {}", variations);
        return variations;
    }

    private void logToMLflow(String userMessage, String aiResponse, long latencyMs) {
        CompletableFuture.runAsync(() -> {
            try {
                String mlflowUrl = "http://mlflow:5000/api/2.0/mlflow";

                // Step 1: Create a run
                org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
                headers.setContentType(org.springframework.http.MediaType.APPLICATION_JSON);

                Map<String, Object> runBody = new HashMap<>();
                runBody.put("experiment_id", "0"); // Default experiment ID
                runBody.put("run_name", "RAG_ChatQuery_" + UUID.randomUUID().toString().substring(0, 8));

                List<Map<String, String>> tags = new ArrayList<>();
                tags.add(Map.of("key", "user_query", "value", userMessage.substring(0, Math.min(userMessage.length(), 250))));
                tags.add(Map.of("key", "llm_model", "value", ollamaConfig.getChatModel()));
                runBody.put("tags", tags);

                org.springframework.http.HttpEntity<Map<String, Object>> entity = new org.springframework.http.HttpEntity<>(runBody, headers);

                ResponseEntity<Map> response = restTemplate.exchange(
                        mlflowUrl + "/runs/create",
                        HttpMethod.POST,
                        entity,
                        Map.class
                );

                if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                    Map<String, Object> run = (Map<String, Object>) response.getBody().get("run");
                    if (run != null) {
                        Map<String, Object> info = (Map<String, Object>) run.get("info");
                        if (info != null) {
                            String runId = (String) info.get("run_id");

                            // Step 2: Log parameters (model_name, temperature)
                            logParameter(mlflowUrl, runId, "model_name", ollamaConfig.getChatModel());
                            logParameter(mlflowUrl, runId, "temperature", String.valueOf(ollamaConfig.getTemperature()));
                            logParameter(mlflowUrl, runId, "prompt_length", String.valueOf(userMessage.length()));

                            // Step 3: Log metrics (latency_ms, response_length)
                            logMetric(mlflowUrl, runId, "latency_ms", (double) latencyMs);
                            logMetric(mlflowUrl, runId, "response_length", (double) aiResponse.length());

                            log.info("MLflow Tracking: Logged chat query execution under run ID: {}", runId);
                        }
                    }
                }
            } catch (Exception e) {
                // Silently log warning, keeping RAG running even if MLflow is not started
                log.debug("MLflow server not reachable or failed to log metrics: {}", e.getMessage());
            }
        });
    }

    private void logParameter(String mlflowUrl, String runId, String key, String value) {
        try {
            org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
            headers.setContentType(org.springframework.http.MediaType.APPLICATION_JSON);

            Map<String, Object> body = new HashMap<>();
            body.put("run_id", runId);
            body.put("key", key);
            body.put("value", value);

            org.springframework.http.HttpEntity<Map<String, Object>> entity = new org.springframework.http.HttpEntity<>(body, headers);
            restTemplate.exchange(mlflowUrl + "/runs/log-parameter", HttpMethod.POST, entity, String.class);
        } catch (Exception e) {
            log.warn("Failed to log MLflow parameter: {}", key, e);
        }
    }

    private void logMetric(String mlflowUrl, String runId, String key, double value) {
        try {
            org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
            headers.setContentType(org.springframework.http.MediaType.APPLICATION_JSON);

            Map<String, Object> body = new HashMap<>();
            body.put("run_id", runId);
            body.put("key", key);
            body.put("value", value);
            body.put("timestamp", System.currentTimeMillis());
            body.put("step", 0);

            org.springframework.http.HttpEntity<Map<String, Object>> entity = new org.springframework.http.HttpEntity<>(body, headers);
            restTemplate.exchange(mlflowUrl + "/runs/log-metric", HttpMethod.POST, entity, String.class);
        } catch (Exception e) {
            log.warn("Failed to log MLflow metric: {}", key, e);
        }
    }

    public List<ChatMessage> getChatHistory(String ownerUsername, String sessionId) {
        return chatMessageRepository.findByOwnerUsernameAndSessionIdOrderByCreatedAtAsc(ownerUsername, sessionId);
    }

    public List<ChatMessage> getChatHistory(String ownerUsername, String sessionId, Long documentId) {
        return chatMessageRepository.findByOwnerUsernameAndSessionIdAndDocumentIdOrderByCreatedAtAsc(
                ownerUsername, sessionId, documentId);
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
        String result = null;
        for (int attempt = 1; attempt <= llmMaxAttempts; attempt++) {
            result = callLLMOnce(prompt);
            if (!result.startsWith("Sorry, the language model is temporarily unavailable.")
                    && !result.startsWith("Sorry, I could not generate a response.")) {
                return result;
            }
            if (attempt < llmMaxAttempts) {
                try {
                    Thread.sleep(llmRetryBackoffMs * attempt);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    return result;
                }
            }
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private String callLLMOnce(String prompt) {
        long startTime = System.currentTimeMillis();
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(buildChatRequest(prompt, false), headers);

            log.info("Calling local Ollama model: {}", ollamaConfig.getChatModel());

            ResponseEntity<Map> response = restTemplate.exchange(
                    ollamaConfig.getChatUrl(),
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

    private Map<String, Object> buildChatRequest(String prompt, boolean stream) {
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("model", ollamaConfig.getChatModel());
        requestBody.put("messages", List.of(
                Map.of("role", "system",
                        "content", "You are a helpful document assistant. Answer questions accurately based on the provided context."),
                Map.of("role", "user", "content", prompt)));
        requestBody.put("options", Map.of("temperature", ollamaConfig.getTemperature(), "num_predict", 2048));
        requestBody.put("stream", stream);
        return requestBody;
    }

    @SuppressWarnings("unchecked")
    private List<String> searchWeb(String query) {
        if (tavilyApiKey == null || tavilyApiKey.isBlank() || tavilyApiKey.equals("your-tavily-api-key-here")) {
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

            ResponseEntity<Map> response = restTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    entity,
                    Map.class
            );

            List<String> webContexts = new ArrayList<>();
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                List<Map<String, Object>> results = (List<Map<String, Object>>) response.getBody().get("results");
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

    private void streamLLM(String prompt, Consumer<String> onToken) {
        restTemplate.execute(ollamaConfig.getChatUrl(), HttpMethod.POST, request -> {
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

    private ChatResponse convertToResponse(ChatMessage message) {
        List<Long> docIds = new ArrayList<>();
        if (message.getDocumentIds() != null && !message.getDocumentIds().isBlank()) {
            for (String s : message.getDocumentIds().split(",")) {
                try {
                    docIds.add(Long.parseLong(s.trim()));
                } catch (NumberFormatException e) {
                    // Ignore
                }
            }
        }
        return ChatResponse.builder()
                .id(message.getId())
                .sessionId(message.getSessionId())
                .userMessage(message.getUserMessage())
                .aiResponse(message.getAiResponse())
                .sourceChunks(message.getSourceChunks())
                .documentId(message.getDocumentId())
                .documentIds(docIds.isEmpty() ? null : docIds)
                .build();
    }

    public SseEmitter processQueryStream(String ownerUsername, String sessionId, Long documentId,
                                         List<Long> documentIds, String userMessage) {
        SseEmitter emitter = new SseEmitter(180000L);
        ragMetrics.request("stream");

        CompletableFuture.runAsync(() -> {
            try {
                List<Long> finalDocIds = new ArrayList<>();
                if (documentIds != null && !documentIds.isEmpty()) {
                    finalDocIds.addAll(documentIds);
                } else if (documentId != null) {
                    finalDocIds.add(documentId);
                }

                double initialMaxScore = 0.0;
                List<RetrievedChunk> initialChunks = new ArrayList<>();
                Map<RetrievedChunk, String> initialChunkToFileNameMap = new HashMap<>();

                // 1. Initial Retrieval
                for (Long docId : finalDocIds) {
                    Optional<Document> docOpt = documentRepository.findByIdAndOwnerUsername(docId, ownerUsername);
                    if (docOpt.isPresent()) {
                        Document doc = docOpt.get();
                        String vectorCollectionId = doc.getVectorCollectionId();
                        if (vectorCollectionId != null && !vectorCollectionId.isBlank()) {
                            List<RetrievedChunk> chunks = embeddingService.searchChunks(userMessage, vectorCollectionId, 3);
                            for (RetrievedChunk chunk : chunks) {
                                initialChunks.add(chunk);
                                initialChunkToFileNameMap.put(chunk, doc.getFileName());
                                if (chunk.getScore() > initialMaxScore) {
                                    initialMaxScore = chunk.getScore();
                                }
                            }
                        }
                    }
                }

                String sourceChunks = "";
                double finalMaxScore = initialMaxScore;
                String prompt;
                String prefix = "";
                ragMetrics.confidence(initialMaxScore);

                if (initialMaxScore >= 0.45) {
                    // Standard RAG flow: High Confidence
                    List<String> contextList = new ArrayList<>();
                    for (RetrievedChunk chunk : initialChunks) {
                        String fileName = initialChunkToFileNameMap.get(chunk);
                        contextList.add("[" + fileName + "] " + chunk.getParentText());
                    }
                    sourceChunks = String.join("\n---\n", contextList);
                    prompt = buildPrompt(userMessage, contextList);
                } else {
                    ragMetrics.fallback("corrective_retrieval");
                    // Agentic CRAG Loop: Low Confidence (< 0.45)
                    log.info("RAG confidence is low ({} < 0.45). Activating Agentic Loop...", initialMaxScore);

                    // Step 1: Query Reformulation
                    List<String> queryVariations = reformulateQuery(userMessage);
                    List<String> allQueries = new ArrayList<>();
                    allQueries.add(userMessage);
                    allQueries.addAll(queryVariations);

                    // Step 2: Parallel Re-retrieval
                    List<CompletableFuture<Void>> futures = new ArrayList<>();
                    List<RetrievedChunk> agentChunks = Collections.synchronizedList(new ArrayList<>());
                    Map<RetrievedChunk, String> agentChunkToFileNameMap = Collections.synchronizedMap(new HashMap<>());

                    for (String q : allQueries) {
                        for (Long docId : finalDocIds) {
                            Optional<Document> docOpt = documentRepository.findByIdAndOwnerUsername(docId, ownerUsername);
                            if (docOpt.isPresent()) {
                                Document doc = docOpt.get();
                                String vectorCollectionId = doc.getVectorCollectionId();
                                if (vectorCollectionId != null && !vectorCollectionId.isBlank()) {
                                    futures.add(CompletableFuture.runAsync(() -> {
                                        List<RetrievedChunk> chunks = embeddingService.searchChunks(q, vectorCollectionId, 3);
                                        for (RetrievedChunk chunk : chunks) {
                                            agentChunks.add(chunk);
                                            agentChunkToFileNameMap.put(chunk, doc.getFileName());
                                        }
                                    }));
                                }
                            }
                        }
                    }

                    // Wait for parallel retrievals
                    CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();

                    // Step 3: Deduplicate & Rerank
                    Map<String, RetrievedChunk> uniqueChunks = new HashMap<>();
                    for (RetrievedChunk chunk : agentChunks) {
                        String text = chunk.getText().trim();
                        if (!uniqueChunks.containsKey(text) || uniqueChunks.get(text).getScore() < chunk.getScore()) {
                            uniqueChunks.put(text, chunk);
                        }
                    }

                    List<RetrievedChunk> rerankedChunks = new ArrayList<>(uniqueChunks.values());
                    rerankedChunks.sort((a, b) -> Double.compare(b.getScore(), a.getScore()));

                    double agenticMaxScore = 0.0;
                    if (!rerankedChunks.isEmpty()) {
                        agenticMaxScore = rerankedChunks.get(0).getScore();
                    }
                    finalMaxScore = agenticMaxScore;

                    if (agenticMaxScore >= 0.45) {
                        // Agentic Synthesis
                        List<RetrievedChunk> topChunks = rerankedChunks.subList(0, Math.min(rerankedChunks.size(), 4));
                        List<String> contextList = new ArrayList<>();
                        for (RetrievedChunk chunk : topChunks) {
                            String fileName = agentChunkToFileNameMap.get(chunk);
                            contextList.add("[" + fileName + "] " + chunk.getParentText());
                        }
                        sourceChunks = String.join("\n---\n", contextList);
                        prompt = buildPrompt(userMessage, contextList);
                        prefix = "🤖 [Agentic Workflow Activated: Query Reformulation & Parallel retrieval executed because initial RAG confidence was "
                                + String.format(Locale.US, "%.1f", initialMaxScore * 100) + "%]\n\n";
                    } else {
                        // Deep Reasoning Fallback with Web Search
                        log.info("Agentic re-retrieval yielded low score ({} < 0.45). Attempting Web Search Fallback...", agenticMaxScore);
                        List<String> webContexts = searchWeb(userMessage);

                        if (!webContexts.isEmpty()) {
                            ragMetrics.fallback("web_search");
                            sourceChunks = String.join("\n---\n", webContexts);
                            prompt = buildPrompt(userMessage, webContexts);
                            prefix = "🌐 [Độ tin cậy tài liệu thấp. Đang bổ sung ngữ cảnh trực tuyến từ Web Search...]\n\n";
                        } else {
                            ragMetrics.fallback("general_knowledge");
                            prompt = "The user is asking a question that is NOT covered by the loaded documents (retrieval confidence is too low, max score: "
                                    + agenticMaxScore + "). Please use your deep reasoning, internal knowledge, and general knowledge to answer the question as comprehensively and accurately as possible.\n\n"
                                    + "User Question: " + userMessage;
                            prefix = "⚠️ Độ tin cậy thấp (RAG Confidence < 45%). Đang kích hoạt chế độ Suy Luận Sâu của Agent...\n\n";
                        }
                    }
                }

                // Convert document IDs to comma-separated string for DB
                String docIdsStr = null;
                if (!finalDocIds.isEmpty()) {
                    List<String> strIds = new ArrayList<>();
                    for (Long id : finalDocIds) {
                        strIds.add(id.toString());
                    }
                    docIdsStr = String.join(",", strIds);
                }

                // Send metadata event
                Map<String, Object> metaEvent = new HashMap<>();
                metaEvent.put("sourceChunks", sourceChunks.isEmpty() ? null : sourceChunks);
                metaEvent.put("prefix", prefix);
                metaEvent.put("documentId", documentId != null ? documentId : (finalDocIds.isEmpty() ? null : finalDocIds.get(0)));
                metaEvent.put("documentIds", finalDocIds);

                emitter.send(SseEmitter.event().name("metadata").data(metaEvent));

                // If prefix is present, send it immediately as a text chunk
                if (!prefix.isEmpty()) {
                    emitter.send(SseEmitter.event().name("chunk").data(prefix));
                }

                StringBuilder aiResponseBuilder = new StringBuilder(prefix);
                final String finalSourceChunks = sourceChunks;
                final String finalDocIdsStr = docIdsStr;
                final long startTime = System.currentTimeMillis();

                streamLLM(prompt, token -> {
                    aiResponseBuilder.append(token);
                    try {
                        emitter.send(SseEmitter.event().name("chunk").data(token));
                    } catch (IOException e) {
                        throw new IllegalStateException("SSE client disconnected during stream", e);
                    }
                });

                String fullResponse = aiResponseBuilder.toString();
                long latencyMs = System.currentTimeMillis() - startTime;
                logToMLflow(userMessage, fullResponse, latencyMs);

                ChatMessage chatMessage = ChatMessage.builder()
                        .sessionId(sessionId)
                        .ownerUsername(ownerUsername)
                        .documentId(documentId != null ? documentId : (finalDocIds.isEmpty() ? null : finalDocIds.get(0)))
                        .documentIds(finalDocIdsStr)
                        .userMessage(userMessage)
                        .aiResponse(fullResponse)
                        .sourceChunks(finalSourceChunks.isEmpty() ? null : finalSourceChunks)
                        .build();
                ChatMessage saved = chatMessageRepository.save(chatMessage);

                ChatResponse responseDto = convertToResponse(saved);
                emitter.send(SseEmitter.event().name("complete").data(responseDto));
                emitter.complete();

            } catch (Exception e) {
                log.error("Error in local Ollama streaming task: {}", e.getMessage(), e);
                ragMetrics.streamError();
                try {
                    emitter.send(SseEmitter.event().name("error").data(e.getMessage()));
                    emitter.completeWithError(e);
                } catch (Exception ex) {
                    // Ignored
                }
            }
        });

        return emitter;
    }

    public void clearChatHistory(String ownerUsername, String sessionId) {
        List<ChatMessage> messages = getChatHistory(ownerUsername, sessionId);
        chatMessageRepository.deleteAll(messages);
    }
}
