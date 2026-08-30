package com.smartdocchat.security;

import org.springframework.stereotype.Component;

import java.util.regex.Pattern;

/**
 * Heuristic prompt-injection detector for user-supplied messages in the classic
 * chat path.
 *
 * <p>User input is treated as untrusted data. High-severity requests
 * (instruction overwrite, system-prompt disclosure, secrets exfiltration) are
 * rejected before any LLM call; medium-severity requests (suspicious phrasing,
 * encoded payloads) are flagged for logging.
 *
 * <p>This is a defense-in-depth heuristic, not a guarantee: retrieved document
 * content is also isolated from instructions at the prompt layer.
 */
@Component
public class PromptInjectionDetector {

    public enum Severity { NONE, MEDIUM, HIGH }

    private static final Pattern[] HIGH_SIGNATURES = {
            Pattern.compile("(?i)ignore\\s+(all\\s+)?(previous|prior)\\s+(instructions?|prompts?|rules)"),
            Pattern.compile("(?i)disregard\\s+(all\\s+)?(previous|prior)\\s+(instructions?|prompts?|rules)"),
            Pattern.compile("(?i)forget\\s+(all\\s+)?(previous|prior)\\s+(instructions?|prompts?|rules)"),
            Pattern.compile("(?i)(reveal|show|print|display|output|tell)\\s+((me|your|yours|the)\\s+)*(system|developer)\\s+prompt"),
            Pattern.compile("(?i)return\\s+(the\\s+)?(system|developer)\\s+prompt"),
            Pattern.compile("(?i)(give|share)\\s+me\\s+the\\s+(system|developer)\\s+prompt"),
            Pattern.compile("(?i)you\\s+are\\s+now\\s+(an?\\s+|a\\s+)?unfiltered"),
            Pattern.compile("(?i)act\\s+as\\s+if\\s+you\\s+have\\s+no\\s+(rules|restrictions|guidelines|limitations)"),
            Pattern.compile("(?i)dump\\s+(all\\s+)?(your\\s+|the\\s+)?(system|developer)\\s+prompt"),
            Pattern.compile("(?i)do\\s+not\\s+follow\\s+(the\\s+)?(instructions?|rules|guidelines)"),
            Pattern.compile("(?i)you\\s+must\\s+ignore\\s+(the\\s+)?(instructions?|rules|guidelines)"),
            Pattern.compile("(?i)bypass\\s+(your|the)\\s+(rules|guidelines|restrictions|safety)"),
            Pattern.compile("(?i)(access|obtain|get|return|reveal)\\s+(the\\s+)?(secrets?|api\\s*keys?|passwords?)") };

    private static final Pattern[] MEDIUM_SIGNATURES = {
            Pattern.compile("(?i)(system|developer)\\s*prompt"),
            Pattern.compile("(?i)(instructions?|rules?|guidelines?)\\s+(was|were|are)\\s+(changed|overridden|ignored|ignoring|updated|new)"),
            Pattern.compile("(?i)role\\s*[:=]\\s*(system|developer)"),
            Pattern.compile("<(system|developer)>") };

    private static final int MAX_TRUSTED_LENGTH = 8000;
    private static final int MAX_REPETITION = 12;
    private static final int REPEATED_WORD_MIN_LENGTH = 5;

    /**
     * Classifies the severity of a user message.
     *
     * @return HIGH for instruction-override/system-prompt-disclosure attempts,
     *         MEDIUM for suspicious-but-inconclusive messages, NONE otherwise.
     */
    public Severity analyze(String input) {
        if (input == null || input.isBlank()) {
            return Severity.NONE;
        }
        if (input.length() > MAX_TRUSTED_LENGTH) {
            return Severity.HIGH;
        }

        String normalized = input.toLowerCase();
        normalized = normalizeLookalikes(normalized);
        for (Pattern pattern : HIGH_SIGNATURES) {
            if (pattern.matcher(normalized).find()) {
                return Severity.HIGH;
            }
        }
        for (Pattern pattern : MEDIUM_SIGNATURES) {
            if (pattern.matcher(normalized).find()) {
                return Severity.MEDIUM;
            }
        }
        if (looksEncoded(normalized) || hasPathologicalRepetition(normalized)) {
            return Severity.MEDIUM;
        }
        return Severity.NONE;
    }

    /**
     * Maps common Unicode look-alike characters (Cyrillic, Greek) that visually
     * resemble Latin letters onto their ASCII equivalents, so obfuscated
     * injections like "іgnore" (Cyrillic і) cannot slip past the regex matcher.
     */
    private static String normalizeLookalikes(String text) {
        if (text == null) {
            return null;
        }
        StringBuilder sb = new StringBuilder(text.length());
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            switch (c) {
                case 'і': case 'І': sb.append('i'); break;
                case 'е': case 'Е': sb.append('e'); break;
                case 'а': case 'А': sb.append('a'); break;
                case 'о': case 'О': sb.append('o'); break;
                case 'с': case 'С': sb.append('c'); break;
                case 'р': case 'Р': sb.append('p'); break;
                case 'ѕ': case 'Ѕ': sb.append('s'); break;
                case 'х': case 'Х': sb.append('x'); break;
                case 'у': case 'У': sb.append('u'); break;
                case 'п': case 'П': sb.append('n'); break;
                case 'м': case 'М': sb.append('m'); break;
                default: sb.append(c);
            }
        }
        return sb.toString();
    }

    /** Detects encoded payloads: base64 markers, hex blobs, heavy URL encoding. */
    private boolean looksEncoded(String normalized) {
        int base64Markers = countOccurrences(normalized, "base64");
        int encodingMarkers = countOccurrences(normalized, "encoded")
                + countOccurrences(normalized, "decod");
        return base64Markers >= 1 && encodingMarkers >= 1;
    }

    /**
     * Flags pathological repetition (e.g. a single word repeated tens of times),
     * which is common in obfuscated injection payloads.
     */
    private boolean hasPathologicalRepetition(String normalized) {
        String[] words = normalized.split("\\W+");
        String previous = "";
        int streak = 1;
        for (String word : words) {
            if (word.equals(previous) && word.length() >= REPEATED_WORD_MIN_LENGTH) {
                streak++;
                if (streak >= MAX_REPETITION) {
                    return true;
                }
            } else {
                streak = 1;
                previous = word;
            }
        }
        return false;
    }

    private int countOccurrences(String text, String needle) {
        int count = 0;
        int idx = 0;
        while ((idx = text.indexOf(needle, idx)) >= 0) {
            count++;
            idx += needle.length();
        }
        return count;
    }
}