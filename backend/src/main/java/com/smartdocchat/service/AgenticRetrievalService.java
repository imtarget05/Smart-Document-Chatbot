package com.smartdocchat.service;

import com.smartdocchat.dto.RetrievedChunk;
import com.smartdocchat.entity.Document;
import com.smartdocchat.repository.DocumentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.Locale;
import java.util.concurrent.CompletableFuture;

/**
 * AgenticRetrievalService — Single Responsibility: execute the RAG and Agentic
 * CRAG retrieval pipeline.
 *
 * <p>Extracted from {@link ChatService} to eliminate the duplicate CRAG loop that
 * existed in both {@code processQuery} (sync) and {@code processQueryStream} (SSE).
 *
 * <p>This service is stateless and performs <em>no</em> LLM inference or persistence.
 * It only retrieves, deduplicates, and reranks document chunks.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class AgenticRetrievalService {

    private static final double CONFIDENCE_THRESHOLD = 0.45;

    private final DocumentRepository documentRepository;
    private final EmbeddingService embeddingService;
    private final MessageHandler messageHandler;

    // -----------------------------------------------------------------------
    // Public API
    // -----------------------------------------------------------------------

    /**
     * Result of a full retrieval pass (initial or agentic).
     *
     * @param chunks       Top-K de-duplicated, re-ranked chunks
     * @param maxScore     Highest cosine similarity score among the retrieved chunks
     * @param strategy     One of: "direct", "corrective", "web_search", "general_knowledge"
     * @param usedAgenticLoop Whether the CRAG loop was triggered
     */
    public record RetrievalResult(
            List<RetrievedChunk> chunks,
            Map<RetrievedChunk, String> chunkFileNames,
            Map<RetrievedChunk, Long> chunkDocumentIds,
            double maxScore,
            String strategy,
            boolean usedAgenticLoop
    ) {}

    /**
     * Perform the full retrieval pipeline for a user query.
     *
     * <ol>
     *   <li>Initial vector search across all requested documents</li>
     *   <li>If confidence &lt; 0.45 <em>or</em> forced flags are set → CRAG loop
     *       (query reformulation + parallel re-retrieval + dedup + rerank)</li>
     *   <li>If still low confidence → web-search fallback (returns empty chunks)</li>
     *   <li>If no web results → general-knowledge fallback (returns empty chunks)</li>
     * </ol>
     *
     * @param ownerUsername  The authenticated user's username (for document ownership check)
     * @param docIds         Document IDs to search within
     * @param userMessage    The user's raw query
     * @param forceWebSearch Override: always trigger web search
     * @param forceDeepThinking Override: annotate prompt for deep reasoning
     * @return A {@link RetrievalResult} with chunks, file-name mapping and the resolved strategy
     */
    public RetrievalResult retrieve(
            String ownerUsername,
            List<Long> docIds,
            String userMessage,
            boolean forceWebSearch,
            boolean forceDeepThinking
    ) {
        // ── Step 1: Initial retrieval ────────────────────────────────────────
        InitialRetrieval initial = initialRetrieve(ownerUsername, docIds, userMessage);

        boolean agenticNeeded = (initial.maxScore() < CONFIDENCE_THRESHOLD)
                || forceDeepThinking
                || forceWebSearch;

        if (!agenticNeeded) {
            // High-confidence direct RAG — no CRAG loop needed
            return new RetrievalResult(
                    initial.chunks(),
                    initial.chunkFileNames(),
                    initial.chunkDocumentIds(),
                    initial.maxScore(),
                    "direct",
                    false
            );
        }

        // ── Step 2: CRAG Loop — query reformulation + parallel re-retrieval ──
        log.info("CRAG loop activated. Confidence={}, forceWebSearch={}, forceDeepThinking={}",
                String.format(Locale.US, "%.2f", initial.maxScore()), forceWebSearch, forceDeepThinking);

        List<String> allQueries = new ArrayList<>();
        allQueries.add(userMessage);
        allQueries.addAll(messageHandler.reformulateQuery(userMessage));

        List<RetrievedChunk> agentChunks = Collections.synchronizedList(new ArrayList<>());
        Map<RetrievedChunk, String> agentChunkFileNames = Collections.synchronizedMap(new HashMap<>());
        Map<RetrievedChunk, Long> agentChunkDocumentIds = Collections.synchronizedMap(new HashMap<>());
        List<CompletableFuture<Void>> futures = new ArrayList<>();

        for (String q : allQueries) {
            for (Long docId : docIds) {
                Optional<Document> docOpt =
                        documentRepository.findByIdAndOwnerUsername(docId, ownerUsername);
                if (docOpt.isPresent()) {
                    Document doc = docOpt.get();
                    String vectorCollectionId = doc.getVectorCollectionId();
                    if (vectorCollectionId != null && !vectorCollectionId.isBlank()) {
                        futures.add(CompletableFuture.runAsync(() -> {
                            List<RetrievedChunk> chunks =
                                    embeddingService.searchChunks(q, vectorCollectionId, 3);
                            for (RetrievedChunk chunk : chunks) {
                                agentChunks.add(chunk);
                                agentChunkFileNames.put(chunk, doc.getFileName());
                                agentChunkDocumentIds.put(chunk, doc.getId());
                            }
                        }));
                    }
                }
            }
        }
        CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();

        List<RetrievedChunk> reranked = deduplicateAndRerank(agentChunks);
        double agenticMaxScore = reranked.isEmpty() ? 0.0 : reranked.get(0).getScore();

        // ── Step 3: Decide final strategy ───────────────────────────────────
        if (agenticMaxScore >= CONFIDENCE_THRESHOLD && !forceWebSearch) {
            // Corrective RAG succeeded
            return new RetrievalResult(reranked, agentChunkFileNames, agentChunkDocumentIds, agenticMaxScore, "corrective", true);
        }

        // Chunks insufficient — caller must handle web-search / general-knowledge prompt
        // Return empty chunks so ChatService knows to fall back
        String strategy = forceWebSearch ? "web_search" : "general_knowledge";
        return new RetrievalResult(Collections.emptyList(), Collections.emptyMap(), Collections.emptyMap(), agenticMaxScore, strategy, true);
    }

    // -----------------------------------------------------------------------
    // Internal helpers
    // -----------------------------------------------------------------------

    private record InitialRetrieval(
            List<RetrievedChunk> chunks,
            Map<RetrievedChunk, String> chunkFileNames,
            Map<RetrievedChunk, Long> chunkDocumentIds,
            double maxScore
    ) {}

    private InitialRetrieval initialRetrieve(
            String ownerUsername, List<Long> docIds, String userMessage
    ) {
        List<RetrievedChunk> chunks = new ArrayList<>();
        Map<RetrievedChunk, String> chunkFileNames = new HashMap<>();
        Map<RetrievedChunk, Long> chunkDocumentIds = new HashMap<>();
        double maxScore = 0.0;

        for (Long docId : docIds) {
            Optional<Document> docOpt =
                    documentRepository.findByIdAndOwnerUsername(docId, ownerUsername);
            if (docOpt.isEmpty()) continue;
            Document doc = docOpt.get();
            String vectorCollectionId = doc.getVectorCollectionId();
            if (vectorCollectionId == null || vectorCollectionId.isBlank()) continue;

            List<RetrievedChunk> docChunks =
                    embeddingService.searchChunks(userMessage, vectorCollectionId, 3);
            for (RetrievedChunk chunk : docChunks) {
                chunks.add(chunk);
                chunkFileNames.put(chunk, doc.getFileName());
                chunkDocumentIds.put(chunk, doc.getId());
                if (chunk.getScore() > maxScore) {
                    maxScore = chunk.getScore();
                }
            }
        }

        return new InitialRetrieval(chunks, chunkFileNames, chunkDocumentIds, maxScore);
    }

    /**
     * De-duplicate chunks by text and sort descending by similarity score.
     */
    public List<RetrievedChunk> deduplicateAndRerank(List<RetrievedChunk> chunks) {
        Map<String, RetrievedChunk> unique = new HashMap<>();
        for (RetrievedChunk chunk : chunks) {
            String text = chunk.getText().trim();
            if (!unique.containsKey(text) || unique.get(text).getScore() < chunk.getScore()) {
                unique.put(text, chunk);
            }
        }
        List<RetrievedChunk> ranked = new ArrayList<>(unique.values());
        ranked.sort((a, b) -> Double.compare(b.getScore(), a.getScore()));
        return ranked;
    }

    /**
     * Build context strings from chunks for inclusion in the LLM prompt.
     */
    public List<String> buildContextList(
            List<RetrievedChunk> chunks, Map<RetrievedChunk, String> fileNameMap
    ) {
        List<String> contextList = new ArrayList<>();
        for (RetrievedChunk chunk : chunks) {
            String fileName = fileNameMap.getOrDefault(chunk, "document");
            contextList.add("[" + fileName + "] " + chunk.getParentText());
        }
        return contextList;
    }
}
