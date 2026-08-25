package com.smartdocchat.util;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Article-aware parser for Vietnamese legal document structure (Decision 13).
 * Recognises the Chương / Điều / Khoản / Điểm hierarchy.
 *
 * Safety: no content is silently dropped; documents without "Điều" markers
 * return an empty list so callers fall back to generic chunking; legal
 * labels are only attached when observed in the text (null over fabrication).
 */
@Component
public class LegalStructureParser {

    private static final Pattern CHAPTER =
            Pattern.compile("(?i)^\\s*Chương\\s+([IVXLCDM0-9]+)\\b");
    private static final Pattern ARTICLE =
            Pattern.compile("(?i)^\\s*Điều\\s+(\\d+)\\s*[.:：\\-–—]?\\s*(.*)$");
    private static final Pattern CLAUSE = Pattern.compile("^\\s*(\\d{1,3})\\s*[.)]\\s+");
    private static final Pattern POINT = Pattern.compile("^\\s*([a-zA-ZđĐ])\\s*\\)\\s+");

    private static final int MAX_UNIT_CHARS = 4000;

    /** One addressable legal evidence unit. All labels nullable. */
    public record StructuredUnit(String chapter, String article, String clause, String point, String text) {
    }

    /** Parses text into structured legal units; empty when no article structure. */
    public List<StructuredUnit> parse(String text) {
        if (text == null || text.isBlank()) {
            return List.of();
        }
        if (!Pattern.compile("(?im)^\\s*Điều\\s+\\d+").matcher(text).find()) {
            return List.of();
        }

        List<StructuredUnit> units = new ArrayList<>();
        String chapter = null;
        String article = null;
        String clause = null;
        String point = null;
        StringBuilder buffer = new StringBuilder();

        for (String line : text.split("\\r?\\n")) {
            if (CHAPTER.matcher(line).lookingAt()) {
                // A chapter ends the current unit; its label applies to all
                // following articles.
                flush(units, chapter, article, clause, point, buffer);
                chapter = chapterLabel(line);
                article = null;
                continue;
            }
            Matcher m = ARTICLE.matcher(line);
            if (m.matches()) {
                flush(units, chapter, article, clause, point, buffer); // closes previous unit incl. preamble
                article = m.group(1);
                clause = null;
                point = null;
                buffer.append(articleHeading(article, m.group(2))).append('\n');
                continue;
            }
            if (article == null) {
                buffer.append(line).append('\n'); // preamble before first article
                continue;
            }
            if ((m = CLAUSE.matcher(line)).lookingAt()) {
                flush(units, chapter, article, clause, point, buffer);
                clause = m.group(1);
                point = null;
                buffer.append(line.trim()).append('\n');
                continue;
            }
            if (clause != null && (m = POINT.matcher(line)).lookingAt()) {
                flush(units, chapter, article, clause, point, buffer);
                point = m.group(1);
                buffer.append(line.trim()).append('\n');
                continue;
            }
            buffer.append(line).append('\n');
        }
        flush(units, chapter, article, clause, point, buffer);

        return units;
    }

    /** True when the document contains Vietnamese article structure. */
    public boolean hasLegalStructure(String text) {
        return !parse(text).isEmpty();
    }

    private void flush(List<StructuredUnit> units, String chapter, String article,
                       String clause, String point, StringBuilder buffer) {
        String body = buffer.toString().strip();
        buffer.setLength(0);
        if (body.isEmpty()) {
            return;
        }
        if (body.length() <= MAX_UNIT_CHARS) {
            units.add(new StructuredUnit(chapter, article, clause, point, body));
            return;
        }
        // Split oversized units on whitespace boundaries; labels are preserved
        // on every part so no evidence becomes unaddressable.
        for (int i = 0; i < body.length(); i += MAX_UNIT_CHARS) {
            int end = Math.min(body.length(), i + MAX_UNIT_CHARS);
            while (end < body.length() && !Character.isWhitespace(body.charAt(end - 1))) {
                end++;
            }
            units.add(new StructuredUnit(chapter, article, clause, point, body.substring(i, end).strip()));
        }
    }

    private String chapterLabel(String line) {
        Matcher m = CHAPTER.matcher(line);
        return m.lookingAt() ? m.group(1) : null;
    }

    private String articleHeading(String number, String title) {
        return (title == null || title.isBlank())
                ? "Điều " + number
                : "Điều " + number + ". " + title.strip();
    }
}