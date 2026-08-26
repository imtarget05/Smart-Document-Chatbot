package com.smartdocchat.util;

import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Benchmark-driven lexical improvements for Vietnamese queries (Blueprint #35):
 * one change at a time, each with evidence.
 *
 * Change 1 — Vietnamese function-word stoplist in matchTerms(): particles like
 * "thống" (from hệ thống), "cách", "dùng", "nào" carry zero topical signal yet
 * inflate the coverage denominator, dragging legitimate queries toward/below
 * MIN_SCORE. Evidence: diag run 2026-08-26, doc #101, q22/q26/q29 no_evidence.
 *
 * Change 2 — adjacent-word bigrams emitted as phrase units ("concurrent users",
 * "sinh vector"): Vietnamese compounds lose meaning when split into syllables;
 * a matched phrase must boost the correct chunk instead of vanishing.
 */
class LegalQueryNormalizerVietnameseTest {

    private final LegalQueryNormalizer normalizer = new LegalQueryNormalizer();

    @Test
    void removesFunctionWordsFromMatchTerms() {
        Set<String> terms = normalizer.matchTerms(
                "Cách hệ thống xử lý concurrent users?");
        assertFalse(terms.contains("thong"),
                "'thống' (hệ thống) là từ công năng, không mang tín hiệu chủ đề");
        assertFalse(terms.contains("cach"), "'cách' là từ nghi vấn công năng");
        assertTrue(terms.contains("concurrent"), "từ nội dung phải giữ lại");
        assertTrue(terms.contains("users"));
    }

    @Test
    void vietnameseCompoundPhrasesEarnBonusInScoring() {
        LegalQueryNormalizer normalizer = new LegalQueryNormalizer();
        String query = "Cách hệ thống xử lý concurrent users?";
        String matchingChunk = normalizer.foldContent(
                "Xử lý concurrent users bằng connection pool Hikari giới hạn kết nối PostgreSQL.");
        String otherChunk = normalizer.foldContent(
                "Backup định kỳ PostgreSQL bằng pg_dump hàng ngày.");

        double bonusMatch = normalizer.phraseBonus(query, matchingChunk, 5, 0.15);
        double bonusOther = normalizer.phraseBonus(query, otherChunk, 5, 0.15);
        assertTrue(bonusMatch > 0, "Cụm 'concurrent users' xuất hiện trong chunk phải được thưởng");
        assertEquals(0.0, bonusOther, 1e-9, "Chunk không chứa cụm thì không thưởng");
    }

    @Test
    void englishQueriesKeepLegacyBehaviour() {
        Set<String> terms = normalizer.matchTerms("insurance renewal policy");
        assertTrue(terms.contains("insurance"));
        assertTrue(terms.contains("renewal"));
        assertTrue(terms.contains("policy"));
        assertFalse(terms.contains("insurance renewal"),
                "tiếng Anh không ghép bigram để tránh phình tập term");
    }
}
