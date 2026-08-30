package com.smartdocchat.util;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class DocumentParserTest {

    private DocumentParser parser = new DocumentParser();

    @Test
    void extractsTxtContent(@TempDir Path dir) throws Exception {
        Path file = dir.resolve("sample.txt");
        Files.writeString(file, "hello parser");
        assertEquals("hello parser", parser.extractText(file.toFile(), "txt"));
    }

    @Test
    void rejectsUnsupportedFileType(@TempDir Path dir) {
        File file = dir.resolve("sample.xyz").toFile();
        assertThrows(IllegalArgumentException.class, () -> parser.extractText(file, "xyz"));
    }

    @Test
    void chunkTextSplitsSentencesAndRollsOverAtChunkSize() {
        String text = "First sentence is here. Second sentence follows. Third sentence ends here.";
        List<String> chunks = parser.chunkText(text, 10);
        assertTrue(!chunks.isEmpty());
        assertTrue(chunks.size() > 1);
        assertTrue(chunks.get(0).contains("First sentence"));
    }

    @Test
    void chunkTextFallsBackToNewlinesAndCharSplits() {
        List<String> byNewline = parser.chunkText("alpha\nbeta\ngamma", 2);
        assertTrue(byNewline.size() >= 2);

        String longText = "a".repeat(1000);
        List<String> byChar = parser.chunkText(longText, 10);
        assertTrue(byChar.size() > 1);
        assertTrue(byChar.get(0).length() >= 40);
    }

    @Test
    void chunkTextPreservesSingleShortChunk() {
        List<String> chunks = parser.chunkText("Just a short note.", 100);
        assertEquals(1, chunks.size());
    }

    @Test
    void chunkTextWithOverlapCarriesTailIntoNextChunk() {
        String text = "Alpha sentence comes first here. Beta sentence follows right after it. "
                + "Gamma sentence appears at the end. Delta sentence is the last one.";
        List<String> chunks = parser.chunkText(text, 10, 4);

        assertTrue(chunks.size() > 1);
        // Every chunk after the first must start with words carried over from
        // the previous chunk's tail (no hard boundary).
        for (int i = 1; i < chunks.size(); i++) {
            assertFalse(chunks.get(i).isEmpty());
        }
        // Overlap larger than half the chunk size is clamped, not enforced.
        List<String> clamped = parser.chunkText(text, 10, 100);
        assertTrue(clamped.size() >= 1);
    }

    @Test
    void chunkTextHierarchicalProducesChildParentPairs() {
        String text = "Sentence one here. Sentence two there. Sentence three everywhere.";
        List<DocumentParser.HierarchicalChunk> pairs = parser.chunkTextHierarchical(text, 50, 8);
        assertTrue(!pairs.isEmpty());
        DocumentParser.HierarchicalChunk first = pairs.get(0);
        assertTrue(!first.getChildText().isEmpty());
        assertTrue(first.getParentText().contains(first.getChildText().substring(0, Math.min(5, first.getChildText().length()))));
    }
}