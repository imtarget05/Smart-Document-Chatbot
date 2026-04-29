package com.smartdocchat.util;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

@Component
public class DocumentParser {

    public String extractText(File file, String fileType) throws IOException {
        if (fileType.equals("pdf")) {
            return extractPdfText(file);
        } else if (fileType.equals("docx") || fileType.equals("doc")) {
            return extractDocxText(file);
        } else if (fileType.equals("txt")) {
            return new String(java.nio.file.Files.readAllBytes(file.toPath()));
        }
        throw new IllegalArgumentException("Unsupported file type: " + fileType);
    }

    private String extractPdfText(File file) throws IOException {
        StringBuilder text = new StringBuilder();
        try (PDDocument document = PDDocument.load(file)) {
            PDFTextStripper stripper = new PDFTextStripper();
            text.append(stripper.getText(document));
        }
        return text.toString();
    }

    private String extractDocxText(File file) throws IOException {
        StringBuilder text = new StringBuilder();
        try (XWPFDocument document = new XWPFDocument(java.nio.file.Files.newInputStream(file.toPath()))) {
            for (XWPFParagraph paragraph : document.getParagraphs()) {
                text.append(paragraph.getText()).append("\n");
            }
        }
        return text.toString();
    }

    public List<String> chunkText(String text, int chunkSize) {
        List<String> chunks = new ArrayList<>();
        String[] sentences = text.split("(?<=[.!?])\\s+");
        
        StringBuilder chunk = new StringBuilder();
        int tokenCount = 0;
        
        for (String sentence : sentences) {
            int sentenceTokens = estimateTokens(sentence);
            
            if (tokenCount + sentenceTokens > chunkSize && chunk.length() > 0) {
                chunks.add(chunk.toString().trim());
                chunk = new StringBuilder();
                tokenCount = 0;
            }
            
            chunk.append(sentence).append(" ");
            tokenCount += sentenceTokens;
        }
        
        if (chunk.length() > 0) {
            chunks.add(chunk.toString().trim());
        }
        
        return chunks;
    }

    private int estimateTokens(String text) {
        // Rough estimation: 1 token ≈ 4 characters
        return (text.length() + 3) / 4;
    }
}
