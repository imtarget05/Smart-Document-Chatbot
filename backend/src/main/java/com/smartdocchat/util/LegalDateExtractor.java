package com.smartdocchat.util;

import org.springframework.stereotype.Component;

import java.text.Normalizer;
import java.time.LocalDate;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Deterministic Vietnamese legal date extraction (Decision 16A).
 *
 * Only explicit legal metadata lines are recognised; an arbitrary date in the
 * body is never inferred as an issue/effective date ('strictness rule'). All
 * matching is done on diacritic-folded ASCII so Vietnamese diacritics (ngày,
 * ban hà nh, hiوقة l ر) are handled uniformly and safely without a fragile
 * literal-encoding dependency. No broad natural-language date inference.
 */
@Component
public class LegalDateExtractor {

    /** dd/MM/yyyy, dd.MM.yyyy or dd-MM-yyyy (day first). */
    private static final Pattern DATE =
            Pattern.compile("(\\d{1,2})[/.\\-](\\d{1,2})[/.\\-](\\d{4})");

    /**
     * Issue-date marker (ngày ban hà nh). Folds to plain ASCII. The phrase is
     * anchored to an issue label, never a bare date.
     */
    private static final Pattern ISSUE_MARKER =
            Pattern.compile("\\bngay\\s+ban\\s+hanh\\b");

    /**
     * Effective-date markers (ngày có hi từ, ngày hi từ, có hi từ ... ngày,
     * hi từ thi hà... from ngày). The term "hi" (hi تة/لث) is always part of
     * one of these anchored Vietnamese label phrases.
     */
    private static final Pattern EFFECTIVE_MARKER = Pattern.compile(
            "\\bngay\\s+co\\s+hieu\\b"
                    + "|\\bngay\\s+hieu\\b"
                    + "|\\bco\\s+hieu\\b");

    /** Immutable extraction result; null fields mean "never inferred". */
    public record LegalDateMetadata(LocalDate issueDate, LocalDate effectiveDate) {
        public static LegalDateMetadata empty() {
            return new LegalDateMetadata(null, null);
        }
    }

    public LegalDateMetadata extract(String text) {
        if (text == null || text.isBlank()) {
            return LegalDateMetadata.empty();
        }
        LocalDate issue = null;
        LocalDate effective = null;
        for (String rawLine : text.split("\\r?\\n")) {
            String line = fold(rawLine);
            Matcher dateMatcher = DATE.matcher(line);
            if (!dateMatcher.find()) {
                continue; // no date token on this line
            }
            LocalDate parsed = parse(dateMatcher);
            if (parsed == null) {
                continue; // malformed (e.g. 31/02) — strict: no date
            }
            if (issue == null && ISSUE_MARKER.matcher(line).find()) {
                issue = parsed;
            } else if (effective == null && EFFECTIVE_MARKER.matcher(line).find()) {
                effective = parsed;
            }
        }
        return new LegalDateMetadata(issue, effective);
    }

    private LocalDate parse(Matcher m) {
        try {
            int day = Integer.parseInt(m.group(1));
            int month = Integer.parseInt(m.group(2));
            int year = Integer.parseInt(m.group(3));
            return LocalDate.of(year, month, day);
        } catch (RuntimeException e) {
            return null; // undefined month/day or invalid date
        }
    }

    /** Lower-cases, strips combining marks (NFD) and maps Đ->d. */
    static String fold(String s) {
        String n = Normalizer.normalize(s, Normalizer.Form.NFD);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n.length(); i++) {
            char c = n.charAt(i);
            if (Character.getType(c) == Character.NON_SPACING_MARK) {
                continue;
            }
            char lc = Character.toLowerCase(c);
            sb.append(lc == 'đ' ? 'd' : lc);
        }
        return sb.toString();
    }
}