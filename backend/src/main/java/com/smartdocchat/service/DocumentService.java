package com.smartdocchat.service;

import com.smartdocchat.entity.Document;
import com.smartdocchat.repository.DocumentRepository;
import com.smartdocchat.util.DocumentParser;
import com.smartdocchat.util.QdrantConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class DocumentService {
    private final DocumentRepository documentRepository;
    private final DocumentParser documentParser;
    private final EmbeddingService embeddingService;
    private final QdrantConfig qdrantConfig;

    private static final String UPLOAD_DIR = "uploads";

    public Document uploadDocument(MultipartFile file) throws IOException {
        // Create upload directory if not exists
        Files.createDirectories(Paths.get(UPLOAD_DIR));

        // Get file extension
        String originalFileName = file.getOriginalFilename();
        String fileExtension = getFileExtension(originalFileName);
        String fileName = UUID.randomUUID() + "." + fileExtension;
        Path filePath = Paths.get(UPLOAD_DIR, fileName);

        // Save file
        Files.write(filePath, file.getBytes());

        // Extract and chunk text
        File savedFile = filePath.toFile();
        String extractedText = documentParser.extractText(savedFile, fileExtension);
        List<String> chunks = documentParser.chunkText(extractedText, 500);

        log.info("Document '{}' extracted with {} chunks", originalFileName, chunks.size());

        // Create embeddings and store in Qdrant
        String collectionId = embeddingService.embedAndStore(fileName, chunks);

        // Save document metadata to database
        Document document = Document.builder()
                .fileName(originalFileName)
                .filePath(filePath.toString())
                .fileType(fileExtension)
                .fileSize(file.getSize())
                .vectorCollectionId(collectionId)
                .chunkCount(chunks.size())
                .build();

        return documentRepository.save(document);
    }

    public List<Document> getAllDocuments() {
        return documentRepository.findByOrderByCreatedAtDesc();
    }

    public Document getDocumentById(Long id) {
        return documentRepository.findById(id).orElseThrow(
                () -> new RuntimeException("Document not found with id: " + id)
        );
    }

    public void deleteDocument(Long id) {
        Document document = getDocumentById(id);
        // Delete from vector DB (implement based on Qdrant API)
        embeddingService.deleteCollection(document.getVectorCollectionId());
        // Delete file
        try {
            Files.deleteIfExists(Paths.get(document.getFilePath()));
        } catch (IOException e) {
            log.error("Error deleting file: {}", document.getFilePath(), e);
        }
        // Delete from database
        documentRepository.delete(document);
    }

    private String getFileExtension(String fileName) {
        if (fileName != null && fileName.contains(".")) {
            return fileName.substring(fileName.lastIndexOf(".") + 1).toLowerCase();
        }
        return "txt";
    }
}
