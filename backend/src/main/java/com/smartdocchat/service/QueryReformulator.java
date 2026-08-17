package com.smartdocchat.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/**
 * Generates alternative phrasings of a low-confidence query so that the
 * Retriever can look for the same information from a different angle.
 * This is the Java equivalent of the agent-service "_reformulate_query".
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class QueryReformulator {

    private static final String SYSTEM_PROMPT =
            "You are a query rewriting assistant for document retrieval. "
                    + "Rewrite the user question so that a keyword search engine can "
                    + "find the same information more easily. Output ONLY the requested "
                    + "number of alternative phrasings, one per line, without numbering.";

    private static final String USER_PROMPT_TEMPLATE =
            "Rewrite the following question into %d alternative phrasing(s) to improve "
                    + "document retrieval. Output ONLY the alternatives, one per line, "
                    + "no numbering.\n\nQuestion: %s";

    private final MessageHandler messageHandler;

    /**
     * Returns up to {@code maxVariants} reformulated queries. Empty when the LLM
     * call fails or produces nothing usable (CRAG then skips reformulation).
     */
    public List<String> reformulate(String query, int maxVariants) {
        if (query == null || query.isBlank() || maxVariants <= 0) {
            return List.of();
        }

        try {
            String userPrompt = USER_PROMPT_TEMPLATE.formatted(maxVariants, query);
            String response = messageHandler.callLLM(SYSTEM_PROMPT, userPrompt);
            List<String> variants = new ArrayList<>();
            for (String line : response.split("\\R")) {
                String candidate = line.strip().replaceAll("^[-*\\d.\\s]+", "");
                if (candidate.length() >= 8 && variants.size() < maxVariants) {
                    variants.add(candidate);
                }
            }
            if (variants.isEmpty()) {
                log.debug("Query reformulation produced no usable variants");
            }
            return variants;
        } catch (Exception e) {
            log.warn("Query reformulation failed: {}", e.getMessage());
            return List.of();
        }
    }
}