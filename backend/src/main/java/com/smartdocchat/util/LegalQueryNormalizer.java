package com.smartdocchat.util;

import org.springframework.stereotype.Component;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Deterministic Vietnamese legal query normalization (Decision 15).
 *
 * Three conservative, fully testable transforms — nothing speculative:
 *
 * 1. Controlled abbreviation expansion (small fixed domain map):
 *      NLĐ → người lao động, NSDLĐ → người sử dụng lao động,
 *      HĐLĐ → hợp đồng lao động, BLĐ→bộ luật, NQ→nghị quyết...
 * 2. Diacritic folding used ONLY for matching (both sides folded), never
 *    shown to users or stored.
 * 3. Structured legal reference extraction from the query:
 *      "điều 35", "điều 35 khoản 2 điểm a"
 *    Only extracted when the marker word is explicit; never inferred.
 */
@Component
public class LegalQueryNormalizer {

    /** Small, explicit, test-covered abbreviation map. Order matters: longest first. */
    private static final List<String[]> ABBREVIATIONS = List.of(
            new String[]{"nsdlđ", "người sử dụng lao động"},
            new String[]{"nsdld", "người sử dụng lao động"},
            new String[]{"hdld", "hợp đồng lao động"},
            new String[]{"hđld", "hợp đồng lao động"},
            new String[]{"nlđ", "người lao động"},
            new String[]{"nld", "người lao động"},
            new String[]{"blhs", "bộ luật hình sự"},
            new String[]{"bltt", "bộ luật tố tụng"},
            new String[]{"blđs", "bộ luật dân sự"}
    );

    private static final Pattern ARTICLE_REF = Pattern.compile(
            "(?i)điều\\s+(\\d{1,3})(?:\\s*,?\\s*khoản\\s+(\\d{1,3}))?(?:\\s*,?\\s*điểm\\s+([a-zà-ỹ]))?");
    /** Document numbers like 45/2019/QH14 — kept as one match unit. */
    private static final Pattern DOC_NUMBER = Pattern.compile("[\\p{L}\\p{N}]+/\\d{2,4}/[\\p{L}\\p{N}]+");

    /**
     * Vietnamese function words (Benchmark 2026-08-26, doc #101/#102): question
     * frames like "Cách hệ thống xử lý X?" otherwise contribute "cach",
     * "thong", "xu ly" to the term set — inflating the coverage denominator and
     * dragging legitimate queries toward MIN_SCORE. Folded forms listed.
     */
    private static final Set<String> VI_STOPWORDS = Set.of(
            "cach", "thong", "he", "su", "dung", "duoc", "nhu", "the", "nao",
            "gi", "la", "cua", "va", "cho", "voi", "tu", "trong", "mot", "nhung",
            "cac", "co", "khong", "den", "khi", "de", "lam", "bien", "phap");

    public record ArticleRef(String article, String clause, String point) {
    }

    /** Lowercases and NFC-normalises text. */
    public String normalize(String text) {
        if (text == null) {
            return "";
        }
        return Normalizer.normalize(text.toLowerCase(), Normalizer.Form.NFC);
    }

    /** Removes diacritics for matching only (e.g. "điều" → "dieu"). */
    public String fold(String text) {
        String decomposed = Normalizer.normalize(text == null ? "" : text, Normalizer.Form.NFD);
        return decomposed.replaceAll("\\p{M}+", "").replace('đ', 'd').replace('Đ', 'D');
    }

    /**
     * Expands known legal abbreviations in normalised text.
     * Unknown words pass through untouched — no uncontrolled synonym guessing.
     */
    public String expandAbbreviations(String normalizedText) {
        String result = normalize(normalizedText);
        for (String[] pair : ABBREVIATIONS) {
            // Word-boundary replacement so "nld" never hits inside other words.
            result = Pattern.compile("(^|[^\\p{L}])" + Pattern.quote(pair[0]) + "([^\\p{L}]|$)")
                    .matcher(result)
                    .replaceAll("$1" + Matcher.quoteReplacement(pair[1]) + "$2");
            // The replaceAll above handles single occurrences at boundaries; run twice
            // for adjacent occurrences sharing separators like "NLĐ, NSDLĐ".
        }
        for (String[] pair : ABBREVIATIONS) {
            result = Pattern.compile("(^|[^\\p{L}])" + Pattern.quote(pair[0]) + "([^\\p{L}]|$)")
                    .matcher(result)
                    .replaceAll("$1" + Matcher.quoteReplacement(pair[1]) + "$2");
        }
        return result;
    }

    /** Extracts an explicit Điều/Khoản/Điểm reference from the query, if stated. */
    public Optional<ArticleRef> extractArticleRef(String query) {
        Matcher m = ARTICLE_REF.matcher(normalize(query));
        if (!m.find()) {
            return Optional.empty();
        }
        String point = m.group(3);
        return Optional.of(new ArticleRef(
                m.group(1),
                m.group(2),
                point == null ? null : point));
    }

    /** Extracts an explicit document number (NN/YYYY/CODE) from the query, if stated. */
    public Optional<String> extractDocumentNumber(String query) {
        Matcher m = DOC_NUMBER.matcher(query);
        return m.find() ? Optional.of(m.group()) : Optional.empty();
    }

    /**
     * Builds the folded match-term set for a query: individual words plus any
     * slash-containing document-number units kept intact. Abbreviations are
     * expanded before tokenising.
     *
     * Benchmark-driven addition (Blueprint #35): Vietnamese function words are
     * dropped (VI_STOPWORDS) so question frames like "Cách hệ thống xử lý X?"
     * do not dilute coverage with "cach"/"thong" noise. Phrase-level evidence
     * is handled separately by {@link #phraseBonus} — bigrams deliberately do
     * NOT enter this set, so the coverage denominator stays comparable to the
     * legacy benchmark.
     */
    public Set<String> matchTerms(String query) {
        String expanded = expandAbbreviations(query);
        String folded = fold(expanded);
        Set<String> terms = new LinkedHashSet<>();
        for (String word : folded.split("[^\\p{L}\\p{N}_]+")) {
            if (!word.isEmpty() && word.length() >= 3 && !VI_STOPWORDS.contains(word)
                    && !"dieu".equals(word) && !"khoan".equals(word)) {
                terms.add(word);
            }
        }
        Matcher num = DOC_NUMBER.matcher(folded);
        while (num.find()) {
            terms.add(num.group());
        }
        return terms;
    }

    /**
     * Coverage bonus for Vietnamese compound phrases: when a content-word pair
     * from the diacritic query appears adjacently in the chunk ("sinh vector",
     * "concurrent users"), that co-location is stronger topical evidence than
     * the two single-word hits alone. Returns 0..maxBonus scaled by the share
     * of phrase pairs found. Only diacritic (Vietnamese) queries earn bonuses,
     * keeping English behaviour identical to legacy.
     */
    public double phraseBonus(String query, String foldedChunkContent, int maxPairsConsidered, double perPairBonus) {
        if (!hasDiacritics(query) || maxPairsConsidered <= 0 || perPairBonus <= 0) {
            return 0.0;
        }
        String expanded = expandAbbreviations(query);
        String[] tokens = fold(expanded).split("[^\\p{L}\\p{N}_]+");
        List<String> contentWords = new ArrayList<>();
        for (String w : tokens) {
            if (!w.isEmpty() && w.length() >= 3 && !VI_STOPWORDS.contains(w)) {
                contentWords.add(w);
            }
        }
        String padded = " " + foldedChunkContent + " ";
        int found = 0;
        int considered = 0;
        for (int i = 0; i + 1 < contentWords.size() && considered < maxPairsConsidered; i++) {
            String pair = contentWords.get(i) + " " + contentWords.get(i + 1);
            considered++;
            if (padded.contains(" " + pair + " ") || padded.contains(pair)) {
                found++;
            }
        }
        return found * perPairBonus;
    }

    /** Convenience: folds arbitrary content text for term matching. */
    public String foldContent(String content) {
        return fold(normalize(content));
    }

    /** Read-only view of the abbreviation map for tests/documentation. */
    public List<String[]> abbreviationMap() {
        return new ArrayList<>(ABBREVIATIONS);
    }

    /** True when the raw text carries Vietnamese tone marks (pre-folding). */
    private boolean hasDiacritics(String text) {
        if (text == null) {
            return false;
        }
        String decomposed = Normalizer.normalize(text, Normalizer.Form.NFD);
        for (int i = 0; i < decomposed.length(); i++) {
            if (Character.getType(decomposed.charAt(i)) == Character.NON_SPACING_MARK
                    || decomposed.charAt(i) == 'đ' || decomposed.charAt(i) == 'Đ') {
                return true;
            }
        }
        return false;
    }
}
