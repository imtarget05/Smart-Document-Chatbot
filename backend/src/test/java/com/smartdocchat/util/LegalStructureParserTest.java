package com.smartdocchat.util;

import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LegalStructureParserTest {

    private final LegalStructureParser parser = new LegalStructureParser();

    private String fixture(String name) throws Exception {
        try (InputStream in = getClass().getClassLoader()
                .getResourceAsStream("fixtures/" + name)) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    // 1. Normal Điều/Khoản text
    @Test
    void extractsArticleAndClause() {
        List<LegalStructureParser.StructuredUnit> units = parser.parse(
                "Văn bản mẫu.\n\nĐiều 1. Phạm vi điều chỉnh\nNội dung chung của điều.\n\n"
                        + "1. Khoản đầu tiên có nội dung.\n2. Khoản thứ hai có nội dung.");
        assertEquals(4, units.size());               // preamble + heading + 2 clauses
        assertNull(units.get(0).article());          // preamble preserved, unlabelled
        assertTrue(units.get(0).text().contains("Văn bản mẫu"));
        assertEquals("1", units.get(1).article());
        assertNull(units.get(1).clause());
        assertEquals("1", units.get(2).clause());
        assertEquals("1", units.get(3).article());
        assertEquals("2", units.get(3).clause());
        assertTrue(units.get(3).text().contains("Khoản thứ hai"));
    }

    // 2. Multiple Điều
    @Test
    void extractsMultipleArticles() {
        List<LegalStructureParser.StructuredUnit> units = parser.parse(
                "Điều 1. Điều thứ nhất\nNội dung điều một.\n\nĐiều 2. Điều thứ hai\nNội dung điều hai.");
        long articleBodies = units.stream().filter(u -> "1".equals(u.article()) || "2".equals(u.article())).count();
        assertEquals(2, articleBodies);
        assertEquals("2", units.get(units.size() - 1).article());
    }

    // 3. Multi-clause Điều
    @Test
    void splitsClausesWithinArticle() {
        List<LegalStructureParser.StructuredUnit> units = parser.parse(
                "Điều 5. Quyền hạn\n1. Khoản một.\n2. Khoản hai.\n3. Khoản ba.");
        List<LegalStructureParser.StructuredUnit> clauses = units.stream()
                .filter(u -> u.clause() != null).toList();
        assertEquals(List.of("1", "2", "3"), clauses.stream().map(LegalStructureParser.StructuredUnit::clause).toList());
        assertTrue(clauses.stream().allMatch(u -> "5".equals(u.article())));
    }

    // 4. Points a/b/c under a clause
    @Test
    void splitsPointsWithinClause() {
        List<LegalStructureParser.StructuredUnit> units = parser.parse(
                "Điều 2. Nội dung\n1. Khoản gốc.\na) Điểm a nội dung.\nb) Điểm b nội dung.\nc) Điểm c nội dung.");
        List<LegalStructureParser.StructuredUnit> points = units.stream()
                .filter(u -> u.point() != null).toList();
        assertEquals(List.of("a", "b", "c"), points.stream().map(LegalStructureParser.StructuredUnit::point).toList());
        points.forEach(p -> {
            assertEquals("2", p.article());
            assertEquals("1", p.clause());
        });
    }

    // 5. Chapter + article
    @Test
    void attachesChapterToFollowingArticles() {
        List<LegalStructureParser.StructuredUnit> units = parser.parse(
                "Chương I\n\nĐiều 1. Mở đầu\nNội dung chương một.\n\nChương II\n\nĐiều 2. Tiếp theo\nNội dung chương hai.");
        LegalStructureParser.StructuredUnit first = units.stream()
                .filter(u -> "1".equals(u.article())).findFirst().orElseThrow();
        LegalStructureParser.StructuredUnit second = units.stream()
                .filter(u -> "2".equals(u.article())).findFirst().orElseThrow();
        assertEquals("I", first.chapter());
        assertEquals("II", second.chapter());
    }

    // 6. Document without legal markers falls back to generic chunking upstream
    @Test
    void returnsEmptyForDocumentWithoutLegalMarkers() {
        String text = "This is a plain engineering report. It has no legal structure at all. "
                + "Second sentence follows here.";
        assertTrue(parser.parse(text).isEmpty());
        assertFalse(parser.hasLegalStructure(text));
    }

    // 7. Malformed numbering must not crash and must not lose content
    @Test
    void handlesMalformedNumberingWithoutContentLoss() {
        String text = "Điều 10\nNội dung không dấu chấm.\n99. Số khoản bất thường.\nzzz) Điểm sai định dạng.";
        List<LegalStructureParser.StructuredUnit> units = parser.parse(text);
        String joined = units.stream().map(LegalStructureParser.StructuredUnit::text)
                .reduce("", (a, b) -> a + " " + b);
        assertTrue(joined.contains("Số khoản bất thường"));
        assertTrue(joined.contains("Điểm sai định dạng"));
    }

    // 8. Punctuation variations of the article marker
    @Test
    void handlesArticlePunctuationVariations() {
        for (String marker : new String[]{"Điều 12. Tiêu đề", "Điều 12: Tiêu đề", "Điều 12 - Tiêu đề", "Điều 12"}) {
            List<LegalStructureParser.StructuredUnit> units =
                    parser.parse(marker + "\nNội dung kiểm tra dấu câu.");
            assertTrue(units.stream().anyMatch(u -> "12".equals(u.article())),
                    "Failed for marker: " + marker);
        }
    }

    // 9. Empty / very short document
    @Test
    void handlesEmptyAndShortDocuments() {
        assertTrue(parser.parse(null).isEmpty());
        assertTrue(parser.parse("").isEmpty());
        assertTrue(parser.parse("   \n  ").isEmpty());
        assertTrue(parser.parse("ngắn").isEmpty());
    }

    // 10. Mixed formatting — no content silently lost (fixture document)
    @Test
    void parsesSyntheticFixtureWithoutContentLoss() throws Exception {
        String text = fixture("legal_synthetic_fixture.txt");
        List<LegalStructureParser.StructuredUnit> units = parser.parse(text);
        assertTrue(parser.hasLegalStructure(text));

        String joined = units.stream().map(LegalStructureParser.StructuredUnit::text)
                .reduce("", (a, b) -> a + " " + b);
        for (String expected : new String[]{
                "Phạm vi điều chỉnh", "Khoản thứ hai của Điều 1", "Điểm b thuộc khoản 2 Điều 1",
                "Quyền và nghĩa vụ", "Điểm a của khoản 1 Điều 2", "Hiệu lực thi hành",
                "không theo mẫu số hóa thông thường", "NOT AN OFFICIAL LEGAL DOCUMENT"}) {
            assertTrue(joined.contains(expected), "Missing content: " + expected);
        }
        assertTrue(units.stream().anyMatch(u ->
                "2".equals(u.article()) && "1".equals(u.clause()) && "a".equals(u.point())));
    }
}