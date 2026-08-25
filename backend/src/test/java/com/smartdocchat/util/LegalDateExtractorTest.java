package com.smartdocchat.util;

import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

/**
 * Decision 16A: deterministic Vietnamese legal date extraction — explicit
 * labelled dates only, never inferred from arbitrary body text.
 *
 * The extractor folds input (NFD strip diacritics + lower-case) before
 * matching, so ASCII test strings below exercise the exact same code path as
 * real Vietnamese diacritics (e.g. "hành"->"hanh", "hi ية"->"hieu").
 */
class LegalDateExtractorTest {

    private final LegalDateExtractor extractor = new LegalDateExtractor();

    @Test
    void extractsIssueDate() {
        LegalDateExtractor.LegalDateMetadata m = extractor.extract("ngay ban hanh: 10/01/2026\nbody.");
        assertEquals(LocalDate.of(2026, 1, 10), m.issueDate());
        assertNull(m.effectiveDate());
    }

    @Test
    void extractsEffectiveDate() {
        LegalDateExtractor.LegalDateMetadata m = extractor.extract("co hieu tu ngay 15/02/2026\nbody.");
        assertNull(m.issueDate());
        assertEquals(LocalDate.of(2026, 2, 15), m.effectiveDate());
    }

    @Test
    void extractsBothDates() {
        LegalDateExtractor.LegalDateMetadata m = extractor.extract(
                "ngay ban hanh: 10/01/2026\nngay co hieu: 15/02/2026\n");
        assertEquals(LocalDate.of(2026, 1, 10), m.issueDate());
        assertEquals(LocalDate.of(2026, 2, 15), m.effectiveDate());
    }

    @Test
    void missingDatesStayNull() {
        assertNull(extractor.extract("Dieu 1. Njo deu").issueDate());
        assertNull(extractor.extract(null).issueDate());
        assertNull(extractor.extract("   \n   ").effectiveDate());
    }

    @Test
    void malformedDateIsNull() {
        LegalDateExtractor.LegalDateMetadata m = extractor.extract("ngay ban hanh: 31/02/2026\n");
        assertNull(m.issueDate());
        assertNull(m.effectiveDate());
    }

    @Test
    void supportsNumericSeparators() {
        assertEquals(LocalDate.of(2026, 1, 10),
                extractor.extract("ngay ban hanh: 10.01.2026\n").issueDate());
        assertEquals(LocalDate.of(2026, 2, 15),
                extractor.extract("ngay ban hanh: 15-02-2026\n").issueDate());
    }

    @Test
    void effectivePhraseHasForceFromDate() {
        // "co hieu ... tu ngay" -> effective
        assertEquals(LocalDate.of(2026, 2, 15),
                extractor.extract("co hieu montant tu ngay 15/02/2026\n").effectiveDate());
        // "ngay hieu ... tu ng"
        assertEquals(LocalDate.of(2026, 2, 16),
                extractor.extract("ngay hieu from tu ngay 16/02/2026\n").effectiveDate());
    }

    @Test
    void arbitraryBodyDateIsNotInferred() {
        LegalDateExtractor.LegalDateMetadata m = extractor.extract(
                "Dieu 4. Le document sign le 01/01/2026 sans libelle legal.\n");
        assertNull(m.issueDate());
        assertNull(m.effectiveDate());
    }

    @Test
    void deadlineSentenceIsNotEffectiveDate() {
        assertNull(extractor.extract("Cet article est applicable dans 30 ngay suivants.\n").effectiveDate());
    }

    @Test
    void multipleUnrelatedDatesAreNotGuessed() {
        LegalDateExtractor.LegalDateMetadata m = extractor.extract(
                "Version du 01/01/2025, rectifie le 05/05/2025, sans libelle.");
        assertNull(m.issueDate());
        assertNull(m.effectiveDate());
    }

    @Test
    void parsesFromDateFixture() throws Exception {
        LegalDateExtractor.LegalDateMetadata m = extractor.extract(fixture("legal_dates_fixture.txt"));
        assertEquals(LocalDate.of(2026, 1, 10), m.issueDate());
        assertEquals(LocalDate.of(2026, 2, 15), m.effectiveDate());
    }

    private String fixture(String name) throws Exception {
        try (InputStream in = getClass().getClassLoader()
                .getResourceAsStream("fixtures/" + name)) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    @Test
    void foldIsStableAndDiacriticAgnostic() {
        assertEquals("ngay ban hanh", LegalDateExtractor.fold("Ngay ban hanh"));
        assertEquals("ngay co hieu", LegalDateExtractor.fold("Ngay Co Hieu"));
    }
}