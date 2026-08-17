package com.smartdocchat.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * Scored retrieval over the chunks stored in PostgreSQL.
 *
 * This is the equivalent of the agent-service Qdrant retrieval for the classic
 * Java Chat endpoints. Each chunk receives a deterministic lexical score in the
 * [0,1] range (word coverage + frequency saturation). The best score becomes the
 * CRAG "confidence" value; low confidence triggers query reformulation/fallback.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class RetrievalService {

    /** A retrieved chunk together with its normalised similarity score (0..1). */
    public record RetrievalResult(String chunk, double score) {
    }

    private final DocumentService documentService;

    /**
     * Retrieves the top-{@code topK} chunks for a query, sorted by descending score.
     * Returns an empty list when there are no lexical matches at all (confidence 0).
     */
    public List<RetrievalResult> retrieve(String ownerUsername, Long documentId, String query, int topK) {
        if (documentId == null || topK <= 0) {
            return List.of();
        }

        List<String> allChunks = documentService.getDocumentChunks(documentId, ownerUsername);
        if (allChunks.isEmpty()) {
            return List.of();
        }

        Set<String> queryWords = tokenize(query);
        if (queryWords.isEmpty()) {
            return List.of();
        }

        List<RetrievalResult> scored = new ArrayList<>();
        for (String chunk : allChunks) {
            if (chunk == null || chunk.isBlank()) {
                continue;
            }
            scored.add(new RetrievalResult(chunk, scoreChunk(chunk, queryWords)));
        }

        scored.sort(Comparator.comparingDouble(RetrievalResult::score).reversed());

        List<RetrievalResult> top = new ArrayList<>();
        for (int i = 0; i < scored.size() && top.size() < topK; i++) {
            if (scored.get(i).score() > 0.0) {
                top.add(scored.get(i));
            }
        }
        return top;
    }

    /**
     * Scores a chunk against the unique query words:
     *   coverage = matchedWords / queryWords                       (0..1)
     *   frequency = min(1, totalHits * 0.15)                       (0..1)
     *   score    = 0.7 * coverage + 0.3 * frequency                (0..1)
     */
    private double scoreChunk(String chunk, Set<String> queryWords) {
        String lower = chunk.toLowerCase();
        Set<String> matched = new LinkedHashSet<>();
        int totalHits = 0;
        for (String word : queryWords) {
            int hits = 0;
            int idx = 0;
            while (idx >= 0 && hits < 3) {
                idx = lower.indexOf(word, idx);
                if (idx >= 0) {
                    hits++;
                    idx += word.length();
                }
            }
            if (hits > 0) {
                matched.add(word);
                totalHits += hits;
            }
        }

        double coverage = matched.size() / (double) queryWords.size();
        double frequency = Math.min(1.0, totalHits * 0.15);
        double score = 0.7 * coverage + 0.3 * frequency;
        return Math.max(0.0, Math.min(1.0, score));
    }

    /** Splits text into a de-duplicated set of words of length >= 3. */
    private Set<String> tokenize(String text) {
        Set<String> words = new LinkedHashSet<>();
        if (text == null || text.isBlank()) {
            return words;
        }
        for (String word : text.toLowerCase().split("\\W+")) {
            if (word.length() >= 3) {
                words.add(word);
            }
        }
        return words;
    }
}