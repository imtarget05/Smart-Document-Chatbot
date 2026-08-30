package com.smartdocchat.util;

import net.sourceforge.tess4j.Tesseract;
import net.sourceforge.tess4j.TesseractException;
import lombok.extern.slf4j.Slf4j;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.rendering.PDFRenderer;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.springframework.stereotype.Component;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

@Slf4j
@Component
public class DocumentParser {

    /**
     * Extract text from document file.
     * Falls back to OCR for scanned/image-based PDFs when text extraction
     * yields too little content.
     */
    public String extractText(File file, String fileType) throws IOException {
        if (fileType.equals("pdf")) {
            String text = extractPdfText(file);
            // Heuristic: if extracted text is too short, the PDF is likely scanned.
            // Fall back to Tesseract OCR.
            if (text.trim().length() < 200) {
                log.warn("PDF text extraction yielded {} chars (< 200) — running OCR fallback for {}",
                        text.trim().length(), file.getName());
                try {
                    String ocrText = runOcrOnPdf(file);
                    if (ocrText != null && ocrText.trim().length() > text.trim().length()) {
                        log.info("OCR fallback succeeded for {}, got {} chars (vs {} from text extraction)",
                                file.getName(), ocrText.trim().length(), text.trim().length());
                        return ocrText;
                    }
                } catch (Exception e) {
                    log.error("OCR fallback failed for {}", file.getName(), e);
                }
            }
            return text;
        } else if (fileType.equals("docx") || fileType.equals("doc")) {
            return extractDocxText(file);
        } else if (fileType.equals("txt")) {
            return new String(Files.readAllBytes(file.toPath()));
        }
        throw new IllegalArgumentException("Unsupported file type: " + fileType);
    }

    /**
     * Run Tesseract OCR on a PDF file page-by-page and concatenate results.
     */
    public String runOcrOnPdf(File pdfFile) throws IOException {
        try (PDDocument document = Loader.loadPDF(pdfFile)) {
            PDFRenderer renderer = new PDFRenderer(document);
            Tesseract tesseract = new Tesseract();
            // Giả định đã cài English language data trong /usr/local/share/tessdata
            // hoặc dùng hệ thống tessdata mặc định.
            tesseract.setLanguage("eng");
            // 0 = legacy Tesseract only, 1 = LSTM only, 2 = combined (tessdata best)
            tesseract.setOcrEngineMode(1);
            tesseract.setPageSegMode(1); // Page segmentation mode: treat as single block of text

            StringBuilder result = new StringBuilder();
            int pageCount = document.getNumberOfPages();

            for (int i = 0; i < pageCount; i++) {
                PDPage page = document.getPage(i);
                // Render page to BufferedImage (dpi ~ 300 to balance quality & speed)
                BufferedImage image = renderer.renderImageWithDPI(i, 300);
                // Tesseract có thểwork trực tiếp từ BufferedImage
                try {
                    // Tesseract 5.x có API nhận BufferedImage
                    String pageText = tesseract.doOCR(image);
                    result.append(pageText).append("\n");
                } catch (TesseractException e) {
                    log.warn("OCR page {} failed, skipping", i, e);
                }
            }
            return result.toString();
        }
    }

    private String extractPdfText(File file) throws IOException {
        StringBuilder text = new StringBuilder();
        try (PDDocument document = Loader.loadPDF(file)) {
            var stripper = new org.apache.pdfbox.text.PDFTextStripper();
            text.append(stripper.getText(document));
        }
        return text.toString();
    }

    private String extractDocxText(File file) throws IOException {
        StringBuilder text = new StringBuilder();
        try (XWPFDocument document = new XWPFDocument(Files.newInputStream(file.toPath()))) {
            for (XWPFParagraph paragraph : document.getParagraphs()) {
                text.append(paragraph.getText()).append("\n");
            }
        }
        return text.toString();
    }

    public List<String> chunkText(String text, int chunkSize) {
        return chunkText(text, chunkSize, 0);
    }

    /**
     * Token-based sentence-aware chunking with optional overlap: the last
     * {@code chunkOverlap} tokens of a chunk are repeated at the start of the
     * next chunk so sentences spanning a boundary keep local context.
     */
    public List<String> chunkText(String text, int chunkSize, int chunkOverlap) {
        List<String> chunks = new ArrayList<>();
        String[] sentences = text.split("(?<=[.!?])\\s+");

        if (sentences.length <= 1) {
            sentences = text.split("\\n+");
        }
        if (sentences.length <= 1) {
            int maxChars = chunkSize * 4;
            List<String> parts = new ArrayList<>();
            for (int i = 0; i < text.length(); i += maxChars) {
                parts.add(text.substring(i, Math.min(i + maxChars, text.length())));
            }
            sentences = parts.toArray(new String[0]);
        }

        int safeOverlap = Math.max(0, Math.min(chunkOverlap, chunkSize / 2));

        StringBuilder chunk = new StringBuilder();
        int tokenCount = 0;

        for (String sentence : sentences) {
            int sentenceTokens = estimateTokens(sentence);

            if (tokenCount + sentenceTokens > chunkSize && chunk.length() > 0) {
                chunks.add(chunk.toString().trim());
                // Start the next chunk with an overlap of the tail of this one.
                String overlapPrefix = extractTail(chunk.toString(), safeOverlap);
                chunk = new StringBuilder(overlapPrefix);
                tokenCount = estimateTokens(overlapPrefix);
            }

            chunk.append(sentence).append(" ");
            tokenCount += sentenceTokens;
        }

        if (chunk.length() > 0 && (chunks.isEmpty() || tokenCount > 0)) {
            String trimmed = chunk.toString().trim();
            // Avoid duplicating the overlap tail as a standalone final chunk.
            if (chunks.isEmpty() || !trimmed.equals(chunks.get(chunks.size() - 1))) {
                chunks.add(trimmed);
            }
        }

        return chunks;
    }

    /** Returns the last ~{@code maxTokens} tokens (words) of {@code text}. */
    private String extractTail(String text, int maxTokens) {
        if (maxTokens <= 0) {
            return "";
        }
        String[] words = text.trim().split("\\s+");
        if (words.length <= maxTokens) {
            return text.trim();
        }
        StringBuilder tail = new StringBuilder();
        for (int i = words.length - maxTokens; i < words.length; i++) {
            tail.append(words[i]).append(" ");
        }
        return tail.toString().trim();
    }

    private int estimateTokens(String text) {
        return (text.length() + 3) / 4;
    }

    public static class HierarchicalChunk {
        private final String childText;
        private final String parentText;

        public HierarchicalChunk(String childText, String parentText) {
            this.childText = childText;
            this.parentText = parentText;
        }

        public String getChildText() {
            return childText;
        }

        public String getParentText() {
            return parentText;
        }
    }

    public List<HierarchicalChunk> chunkTextHierarchical(String text, int parentSize, int childSize) {
        List<HierarchicalChunk> hierarchicalChunks = new ArrayList<>();
        List<String> parentChunks = chunkText(text, parentSize);

        for (String parent : parentChunks) {
            List<String> children = chunkText(parent, childSize);
            for (String child : children) {
                hierarchicalChunks.add(new HierarchicalChunk(child, parent));
            }
        }

        return hierarchicalChunks;
    }
}
