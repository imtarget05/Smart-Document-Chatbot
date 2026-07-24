package com.smartdocchat.service;

import com.smartdocchat.util.LlmConfig;
import com.smartdocchat.util.QdrantConfig;
import com.smartdocchat.util.DocumentParser;
import com.smartdocchat.dto.RetrievedChunk;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.*;

@Service
@RequiredArgsConstructor
@Slf4j
public class EmbeddingService {

    private final LlmConfig llmConfig;
    private final QdrantConfig qdrantConfig;
    private final RestTemplate restTemplate;

    private static final int EMBEDDING_DIMENSION = 768; // nomic-embed-text dimension

    private String qdrantBaseUrl;

    @PostConstruct
    public void init() {
        qdrantBaseUrl = qdrantConfig.getBaseUrl();
        log.info("Qdrant REST API base URL: {}", qdrantBaseUrl);

        // Verify Qdrant connectivity
        try {
            ResponseEntity<String> health = restTemplate.getForEntity(qdrantBaseUrl + "/healthz", String.class);
            log.info("Qdrant health check: {}", health.getStatusCode());
        } catch (Exception e) {
            log.warn("Qdrant not reachable at {}. EmbeddingService will operate in fallback mode.", qdrantBaseUrl);
        }
    }

    /**
     * Generate embeddings for document chunks and store them in Qdrant.
     */
    @SuppressWarnings("unchecked")
    public String embedAndStore(String documentName, List<String> chunks) {
        String collectionId = "doc_" + UUID.randomUUID().toString().replace("-", "");

        try {
            // Step 1: Create collection in Qdrant
            createCollection(collectionId);
            log.info("Created Qdrant collection: {}", collectionId);

            // Step 2: Generate embeddings and upsert in batches
            int batchSize = 20;
            int totalUpserted = 0;
            for (int i = 0; i < chunks.size(); i += batchSize) {
                int end = Math.min(i + batchSize, chunks.size());
                List<String> batchChunks = chunks.subList(i, end);

                List<List<Float>> embeddings = generateEmbeddings(batchChunks);

                if (embeddings.isEmpty() || embeddings.size() != batchChunks.size()) {
                    log.warn("Embedding generation failed or returned mismatched count for batch {}-{}", i, end - 1);
                    continue;
                }

                boolean hasEmpty = false;
                for (List<Float> emb : embeddings) {
                    if (emb.isEmpty()) {
                        hasEmpty = true;
                        break;
                    }
                }
                if (hasEmpty) {
                    log.warn("Embedding generation returned empty vectors for some texts in batch {}-{}", i, end - 1);
                    continue;
                }

                // Build points for upsert
                List<Map<String, Object>> points = new ArrayList<>();
                for (int j = 0; j < batchChunks.size(); j++) {
                    int idx = i + j;
                    Map<String, Object> point = new HashMap<>();
                    point.put("id", idx);
                    point.put("vector", embeddings.get(j));

                    Map<String, Object> payload = new HashMap<>();
                    payload.put("text", batchChunks.get(j));
                    payload.put("chunk_index", idx);
                    payload.put("document_name", documentName);
                    point.put("payload", payload);

                    points.add(point);
                }

                upsertPoints(collectionId, points);
                totalUpserted += batchChunks.size();
                log.debug("Upserted batch {}-{} for collection {}", i, end - 1, collectionId);
            }

            if (totalUpserted > 0) {
                log.info("Successfully stored {} chunks for document '{}' in collection '{}'",
                        totalUpserted, documentName, collectionId);
            } else {
                log.warn("No chunks were stored for document '{}' in collection '{}' (embedding generation failed for all batches)",
                        documentName, collectionId);
            }

        } catch (Exception e) {
            log.error("Error storing embeddings for document '{}': {}", documentName, e.getMessage(), e);
        }

        return collectionId;
    }

    /**
     * Generate embeddings for hierarchical document chunks and store them in Qdrant.
     */
    @SuppressWarnings("unchecked")
    public String embedAndStoreHierarchical(String documentName, List<DocumentParser.HierarchicalChunk> chunks) {
        String collectionId = "doc_" + UUID.randomUUID().toString().replace("-", "");

        try {
            // Step 1: Create collection in Qdrant
            createCollection(collectionId);
            log.info("Created Qdrant collection for hierarchical storage: {}", collectionId);

            // Step 2: Generate embeddings and upsert in batches
            int batchSize = 20;
            int totalUpserted = 0;
            for (int i = 0; i < chunks.size(); i += batchSize) {
                int end = Math.min(i + batchSize, chunks.size());
                List<DocumentParser.HierarchicalChunk> batchChunks = chunks.subList(i, end);

                List<String> childTexts = new ArrayList<>();
                for (DocumentParser.HierarchicalChunk hc : batchChunks) {
                    childTexts.add(hc.getChildText());
                }

                List<List<Float>> embeddings = generateEmbeddings(childTexts);

                if (embeddings.isEmpty() || embeddings.size() != batchChunks.size()) {
                    log.warn("Embedding generation failed or returned mismatched count for hierarchical batch {}-{}", i, end - 1);
                    continue;
                }

                boolean hasEmpty = false;
                for (List<Float> emb : embeddings) {
                    if (emb.isEmpty()) {
                        hasEmpty = true;
                        break;
                    }
                }
                if (hasEmpty) {
                    log.warn("Embedding generation returned empty vectors for some texts in hierarchical batch {}-{}", i, end - 1);
                    continue;
                }

                // Build points for upsert
                List<Map<String, Object>> points = new ArrayList<>();
                for (int j = 0; j < batchChunks.size(); j++) {
                    int idx = i + j;
                    Map<String, Object> point = new HashMap<>();
                    point.put("id", idx);
                    point.put("vector", embeddings.get(j));

                    Map<String, Object> payload = new HashMap<>();
                    payload.put("text", batchChunks.get(j).getChildText());
                    payload.put("parent_text", batchChunks.get(j).getParentText());
                    payload.put("chunk_index", idx);
                    payload.put("document_name", documentName);
                    point.put("payload", payload);

                    points.add(point);
                }

                upsertPoints(collectionId, points);
                totalUpserted += batchChunks.size();
                log.debug("Upserted hierarchical batch {}-{} for collection {}", i, end - 1, collectionId);
            }

            if (totalUpserted > 0) {
                log.info("Successfully stored {} hierarchical chunks for document '{}' in collection '{}'",
                        totalUpserted, documentName, collectionId);
            } else {
                log.warn("No hierarchical chunks were stored for document '{}' in collection '{}' (embedding generation failed for all batches)",
                        documentName, collectionId);
            }

        } catch (Exception e) {
            log.error("Error storing hierarchical embeddings for document '{}': {}", documentName, e.getMessage(), e);
        }

        return collectionId;
    }

    /**
     * Search for relevant chunks using semantic similarity and return RetrievedChunk with scores.
     */
    @SuppressWarnings("unchecked")
    public List<RetrievedChunk> searchChunks(String query, String collectionId, int topK) {
        if (collectionId == null || collectionId.isBlank()) {
            log.warn("Cannot search: collectionId is empty");
            return Collections.emptyList();
        }

        try {
            // Generate query embedding
            List<Float> queryEmbedding = generateEmbedding(query);
            if (queryEmbedding.isEmpty()) {
                log.error("Failed to generate embedding for query");
                return Collections.emptyList();
            }

            // Search in Qdrant
            HttpHeaders headers = buildQdrantHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, Object> searchBody = new HashMap<>();
            searchBody.put("vector", queryEmbedding);
            searchBody.put("limit", topK);
            searchBody.put("with_payload", true);

            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(searchBody, headers);

            ResponseEntity<Map> response = restTemplate.exchange(
                    qdrantBaseUrl + "/collections/" + collectionId + "/points/search",
                    HttpMethod.POST,
                    entity,
                    Map.class
            );

            List<RetrievedChunk> relevantChunks = new ArrayList<>();
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                List<Map<String, Object>> results = (List<Map<String, Object>>) response.getBody().get("result");
                if (results != null) {
                    for (Map<String, Object> result : results) {
                        Map<String, Object> payload = (Map<String, Object>) result.get("payload");
                        Number scoreNum = (Number) result.get("score");
                        double score = scoreNum != null ? scoreNum.doubleValue() : 0.0;
                        if (payload != null && payload.get("text") != null) {
                            String text = payload.get("text").toString();
                            String parentText = payload.containsKey("parent_text") && payload.get("parent_text") != null
                                    ? payload.get("parent_text").toString()
                                    : text;
                            relevantChunks.add(new RetrievedChunk(text, parentText, score));
                        }
                    }
                }
            }

            log.info("Found {} relevant chunks for query in collection '{}'",
                    relevantChunks.size(), collectionId);
            return relevantChunks;

        } catch (Exception e) {
            log.error("Error searching in collection '{}': {}", collectionId, e.getMessage(), e);
            return Collections.emptyList();
        }
    }

    /**
     * Search for relevant chunks using semantic similarity (backward compatible).
     */
    public List<String> search(String query, String collectionId, int topK) {
        List<RetrievedChunk> chunks = searchChunks(query, collectionId, topK);
        List<String> texts = new ArrayList<>();
        for (RetrievedChunk chunk : chunks) {
            texts.add(chunk.getText());
        }
        return texts;
    }

    /**
     * Delete a collection from Qdrant.
     */
    public void deleteCollection(String collectionId) {
        if (collectionId == null || collectionId.isBlank()) {
            log.warn("Cannot delete collection: collectionId is empty");
            return;
        }

        try {
            HttpHeaders headers = buildQdrantHeaders();
            HttpEntity<Void> entity = new HttpEntity<>(headers);

            restTemplate.exchange(
                    qdrantBaseUrl + "/collections/" + collectionId,
                    HttpMethod.DELETE,
                    entity,
                    String.class
            );
            log.info("Deleted Qdrant collection: {}", collectionId);
        } catch (Exception e) {
            log.error("Error deleting Qdrant collection '{}': {}", collectionId, e.getMessage(), e);
        }
    }

    /**
     * Semantic search convenience method using document ID (legacy).
     */
    public List<String> semanticSearch(String query, Long documentId) {
        return search(query, documentId != null ? documentId.toString() : "", 3);
    }

    /**
     * Semantic search using vectorCollectionId directly.
     */
    public List<String> semanticSearchByCollection(String query, String vectorCollectionId) {
        return search(query, vectorCollectionId, 3);
    }

    // ==================== Qdrant REST API Helpers ====================

    private void createCollection(String collectionId) {
        HttpHeaders headers = buildQdrantHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> vectors = new HashMap<>();
        vectors.put("size", EMBEDDING_DIMENSION);
        vectors.put("distance", "Cosine");

        Map<String, Object> body = new HashMap<>();
        body.put("vectors", vectors);

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        restTemplate.exchange(
                qdrantBaseUrl + "/collections/" + collectionId,
                HttpMethod.PUT,
                entity,
                String.class
        );
    }

    private void upsertPoints(String collectionId, List<Map<String, Object>> points) {
        HttpHeaders headers = buildQdrantHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        Map<String, Object> body = new HashMap<>();
        body.put("points", points);

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        ResponseEntity<String> response = restTemplate.exchange(
                qdrantBaseUrl + "/collections/" + collectionId + "/points",
                HttpMethod.PUT,
                entity,
                String.class
        );

        if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
            if (response.getBody().contains("error") || response.getBody().contains("declined")) {
                log.warn("Qdrant upsert reported issue for collection '{}': {}", collectionId, response.getBody());
            }
        } else {
            log.warn("Qdrant upsert returned non-success for collection '{}': {} {}", collectionId,
                    response.getStatusCode(), response.getBody());
        }
    }

    private HttpHeaders buildQdrantHeaders() {
        HttpHeaders headers = new HttpHeaders();
        if (qdrantConfig.getApiKey() != null && !qdrantConfig.getApiKey().isBlank()) {
            headers.set("api-key", qdrantConfig.getApiKey());
        }
        return headers;
    }

    // ==================== Local Ollama Embedding API ====================

    /**
     * Generate embedding for a single text.
     */
    private List<Float> generateEmbedding(String text) {
        List<List<Float>> embeddings = generateEmbeddings(Collections.singletonList(text));
        return embeddings.isEmpty() ? Collections.emptyList() : embeddings.get(0);
    }

    /**
     * Generate embeddings for multiple texts via local Ollama API.
     */
    @SuppressWarnings("unchecked")
    private List<List<Float>> generateEmbeddings(List<String> texts) {
        List<List<Float>> allEmbeddings = new ArrayList<>();

        try {
            String url = llmConfig.getEmbeddingUrl();
            log.info("Generating embeddings using Ollama endpoint: {} with model: {}", url, llmConfig.getEmbeddingModel());

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            int maxChars = 8000;
            for (String text : texts) {
                if (text.length() > maxChars) {
                    text = text.substring(0, maxChars);
                }
                Map<String, Object> requestBody = new HashMap<>();
                requestBody.put("model", llmConfig.getEmbeddingModel());
                requestBody.put("prompt", text);

                HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, headers);

                ResponseEntity<Map> response = restTemplate.exchange(
                        url,
                        HttpMethod.POST,
                        entity,
                        Map.class
                );

                if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                    List<Number> values = (List<Number>) response.getBody().get("embedding");
                    if (values != null) {
                        List<Float> floats = new ArrayList<>();
                        for (Number n : values) {
                            floats.add(n.floatValue());
                        }
                        allEmbeddings.add(floats);
                    } else {
                        log.error("Ollama embedding response did not contain 'embedding' field");
                        allEmbeddings.add(Collections.emptyList());
                    }
                } else {
                    log.error("Ollama embedding API returned non-success status: {}", response.getStatusCode());
                    allEmbeddings.add(Collections.emptyList());
                }
            }

            return allEmbeddings;

        } catch (Exception e) {
            log.error("Error calling Ollama embedding API: {}", e.getMessage(), e);
            return Collections.emptyList();
        }
    }
}
