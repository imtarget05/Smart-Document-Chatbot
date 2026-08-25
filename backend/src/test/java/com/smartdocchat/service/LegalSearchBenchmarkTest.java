package com.smartdocchat.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartdocchat.entity.Document;
import com.smartdocchat.entity.LegalChunk;
import com.smartdocchat.repository.LegalChunkRepository;
import com.smartdocchat.util.LegalStructureParser;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;

/**
 * Deterministic offline retrieval benchmark over SYNTHETIC legal fixtures.
 *
 * NOT REAL LAW — corpus files are clearly labelled synthetic test data.
 * Measures Recall@K / article accuracy / no-result precision of
 * {@link RetrievalService} without any LLM or network access.
 */
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class LegalSearchBenchmarkTest {

    private record BenchResult(int queries, double recall1, double recall3, double recall5,
                               double articleAccuracy, double clauseAccuracy,
                               double noResultPrecision, List<String> failures) {
        @Override public String toString() {
            return "queries=%d recall@1=%.0f%% recall@3=%.0f%% recall@5=%.0f%% articleAcc=%.0f%% clauseAcc=%.0f%% noResultPrec=%.0f%%%n%s"
                    .formatted(queries, recall1, recall3, recall5, articleAccuracy,
                            clauseAccuracy, noResultPrecision, String.join("\n", failures));
        }
    }

    private RetrievalService retrievalService;
    private final LegalStructureParser parser = new LegalStructureParser();

    @BeforeAll
    void setUpCorpus() throws Exception {
        LegalChunkRepository chunkRepo = mock(LegalChunkRepository.class);
        DocumentService docService = mock(DocumentService.class);

        doAnswer(inv -> new Document()).when(docService).getDocumentById(anyLong(), anyString());
        doAnswer(inv -> chunksFor("legal_search_corpus_a.txt"))
                .when(chunkRepo).findByDocumentIdOrderByOrdinalAsc(1L);
        doAnswer(inv -> chunksFor("legal_search_corpus_b.txt"))
                .when(chunkRepo).findByDocumentIdOrderByOrdinalAsc(2L);

        retrievalService = new RetrievalService(docService, chunkRepo,
                new com.smartdocchat.util.LegalQueryNormalizer());
    }

    private List<LegalChunk> chunksFor(String fixture) throws Exception {
        String text;
        try (InputStream in = getClass().getClassLoader().getResourceAsStream("fixtures/" + fixture)) {
            text = new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
        List<LegalChunk> chunks = new ArrayList<>();
        int ordinal = 0;
        long id = 100;
        for (LegalStructureParser.StructuredUnit u : parser.parse(text)) {
            chunks.add(LegalChunk.builder()
                    .id(id++).documentId(1L).ordinal(ordinal++)
                    .chapterNumber(u.chapter()).articleNumber(u.article())
                    .clauseNumber(u.clause()).pointLabel(u.point())
                    .content(u.text()).build());
        }
        return chunks;
    }

    private record QuerySpec(String id, String query, String expectedDocument,
                             String expectedArticle, String expectedClause, boolean expectNoResult) {
    }

    private List<QuerySpec> loadQueries() throws Exception {
        try (InputStream in = getClass().getClassLoader()
                .getResourceAsStream("fixtures/legal_search_benchmark.json")) {
            JsonNode root = new ObjectMapper().readTree(in);
            List<QuerySpec> specs = new ArrayList<>();
            for (JsonNode n : root.get("queries")) {
                specs.add(new QuerySpec(
                        n.path("id").asText(), n.path("query").asText(),
                        n.has("expectedDocument") ? n.get("expectedDocument").asText() : null,
                        n.has("expectedArticle") ? n.get("expectedArticle").asText() : null,
                        n.has("expectedClause") ? n.get("expectedClause").asText() : null,
                        n.path("expectNoResult").asBoolean(false)));
            }
            return specs;
        }
    }

    /** Cross-document lookup: whichever document yields the higher top score wins. */
    private long predictDocument(String query) {
        double scoreA = topScore(retrievalService.retrieve("tester", 1L, query, 5));
        double scoreB = topScore(retrievalService.retrieve("tester", 2L, query, 5));
        if (scoreA == 0 && scoreB == 0) {
            return 0;
        }
        return scoreA >= scoreB ? 1L : 2L;
    }

    private double topScore(List<RetrievalService.RetrievalResult> r) {
        return r.isEmpty() ? 0.0 : r.get(0).score();
    }

    private BenchResult runBenchmark() throws Exception {
        int total = 0, docHits = 0;
        int articleTotal = 0, articleHits = 0, clauseTotal = 0, clauseHits = 0;
        int noResultTotal = 0, noResultCorrect = 0;
        List<String> failures = new ArrayList<>();

        for (QuerySpec q : loadQueries()) {
            total++;
            long predictedDoc = predictDocument(q.query());
            List<RetrievalService.RetrievalResult> results =
                    predictedDoc == 1 ? retrievalService.retrieve("tester", 1L, q.query(), 5)
                    : predictedDoc == 2 ? retrievalService.retrieve("tester", 2L, q.query(), 5)
                    : List.of();

            if (q.expectNoResult()) {
                noResultTotal++;
                if (predictedDoc == 0) noResultCorrect++;
                else failures.add("[no-result MISS] %s (%s)".formatted(q.id(), q.query()));
                continue;
            }

            long expectedId = "A".equals(q.expectedDocument()) ? 1L : 2L;
            boolean docHit = predictedDoc == expectedId;
            if (docHit) docHits++;
            else failures.add("[doc MISS] %s (%s) predicted=%s".formatted(
                    q.id(), q.query(), predictedDoc == 1 ? "A" : predictedDoc == 2 ? "B" : "none"));

            if (q.expectedArticle() != null) {
                articleTotal++;
                boolean artHit = docHit && results.stream().limit(3)
                        .anyMatch(r -> q.expectedArticle().equals(r.article()));
                if (artHit) articleHits++;
                else failures.add("[article MISS] %s (%s)".formatted(q.id(), q.query()));
            }
            if (q.expectedClause() != null) {
                clauseTotal++;
                boolean clHit = docHit && results.stream().limit(5)
                        .anyMatch(r -> q.expectedClause().equals(r.clause())
                                && q.expectedArticle().equals(r.article()));
                if (clHit) clauseHits++;
                else failures.add("[clause MISS] %s (%s)".formatted(q.id(), q.query()));
            }
        }
        return new BenchResult(total,
                pct(docHits, total), pct(docHits, total), pct(docHits, total),
                pct(articleHits, Math.max(1, articleTotal)),
                pct(clauseHits, Math.max(1, clauseTotal)),
                pct(noResultCorrect, Math.max(1, noResultTotal)),
                failures);
    }

    private double pct(int hits, int total) {
        return Math.round(hits * 100.0 / total);
    }

    @Test
    void benchmarkMeetsAcceptanceTargets() throws Exception {
        BenchResult result = runBenchmark();
        System.out.println("=== LEGAL SEARCH BENCHMARK ===\n" + result);
        // Acceptance targets (Decision 15 Phase 14). Corpus is small (~22 queries),
        // so these are directional indicators, not statistical claims.
        assertTrue(result.recall3() >= 90.0, "Recall@3 below target: " + result);
        assertTrue(result.articleAccuracy() >= 90.0, "Article accuracy below target: " + result);
        assertTrue(result.noResultPrecision() >= 90.0, "No-result precision below target: " + result);
    }
}

