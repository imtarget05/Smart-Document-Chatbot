package com.smartdocchat.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class QueryReformulatorTest {

    @Mock private MessageHandler messageHandler;

    private QueryReformulator queryReformulator;

    @BeforeEach
    void setUp() {
        queryReformulator = new QueryReformulator(messageHandler);
    }

    @Test
    void returnsEmptyForBlankQueryOrNonPositiveVariants() {
        assertTrue(queryReformulator.reformulate(null, 3).isEmpty());
        assertTrue(queryReformulator.reformulate("   ", 3).isEmpty());
        assertTrue(queryReformulator.reformulate("question?", 0).isEmpty());
        assertTrue(queryReformulator.reformulate("question?", -1).isEmpty());
    }

    @Test
    void parsesLinesAndStripsNumberingAndBullets() {
        when(messageHandler.callLLM(anyString(), anyString())).thenReturn(
                "- first alternative\n* second alternative\n3. third alternative\n");
        List<String> variants = queryReformulator.reformulate("How to renew insurance?", 3);
        assertEquals(List.of("first alternative", "second alternative", "third alternative"), variants);
    }

    @Test
    void filtersShortCandidatesAndCapsAtMaxVariants() {
        when(messageHandler.callLLM(anyString(), anyString())).thenReturn("abc\na longer valid variant\nanother long one\n");
        List<String> variants = queryReformulator.reformulate("How to renew insurance?", 2);
        assertEquals(2, variants.size());
        assertTrue(variants.get(0).length() >= 8);
    }

    @Test
    void returnsEmptyWhenLlmFails() {
        when(messageHandler.callLLM(anyString(), anyString())).thenThrow(new RuntimeException("llm down"));
        assertTrue(queryReformulator.reformulate("How to renew insurance?", 3).isEmpty());
    }
}