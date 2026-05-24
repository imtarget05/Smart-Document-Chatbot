package com.smartdocchat.service;

import com.smartdocchat.entity.Document;
import com.smartdocchat.repository.DocumentRepository;
import com.smartdocchat.util.DocumentParser;
import com.smartdocchat.util.OpenRouterConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.concurrent.CompletableFuture;

@Service
@RequiredArgsConstructor
@Slf4j
public class DocumentService {
    private final DocumentRepository documentRepository;
    private final DocumentParser documentParser;
    private final EmbeddingService embeddingService;
    private final OpenRouterConfig openRouterConfig;

    @org.springframework.beans.factory.annotation.Value("${airflow.enabled:false}")
    private boolean airflowEnabled;

    @org.springframework.beans.factory.annotation.Value("${airflow.url:http://airflow:8080/api/v1}")
    private String airflowApiUrl;

    private final RestTemplate restTemplate = new RestTemplate();
    private final com.fasterxml.jackson.databind.ObjectMapper objectMapper = new com.fasterxml.jackson.databind.ObjectMapper();

    private static final String UPLOAD_DIR = "uploads";

    public Document uploadDocument(MultipartFile file) throws IOException {
        // Create upload directory if not exists
        Files.createDirectories(Paths.get(UPLOAD_DIR));

        // Get file extension
        String originalFileName = file.getOriginalFilename();
        String fileExtension = getFileExtension(originalFileName);
        String fileName = UUID.randomUUID() + "." + fileExtension;
        Path filePath = Paths.get(UPLOAD_DIR, fileName);

        // Save physical file
        Files.write(filePath, file.getBytes());

        // MLOps Mode: Trigger Airflow DAG
        if (airflowEnabled) {
            log.info("MLOps Mode Enabled: Delegating document '{}' ETL to Airflow", originalFileName);

            Document document = Document.builder()
                    .fileName(originalFileName)
                    .filePath(filePath.toString())
                    .fileType(fileExtension)
                    .fileSize(file.getSize())
                    .status("PROCESSING")
                    .chunkCount(0)
                    .build();

            Document savedDoc = documentRepository.save(document);

            // Trigger Airflow asynchronously to avoid blocking upload API
            CompletableFuture.runAsync(() -> triggerAirflowDAG(savedDoc));

            return savedDoc;
        }

        // Standard Mode: Parse and chunk locally
        File savedFile = filePath.toFile();
        String extractedText = documentParser.extractText(savedFile, fileExtension);
        List<DocumentParser.HierarchicalChunk> chunks = documentParser.chunkTextHierarchical(extractedText, 500, 125);

        log.info("Standard Mode: Document '{}' extracted with {} hierarchical chunks", originalFileName, chunks.size());

        // Create embeddings and store in Qdrant
        String collectionId = embeddingService.embedAndStoreHierarchical(fileName, chunks);

        // Save document metadata to database
        Document document = Document.builder()
                .fileName(originalFileName)
                .filePath(filePath.toString())
                .fileType(fileExtension)
                .fileSize(file.getSize())
                .vectorCollectionId(collectionId)
                .chunkCount(chunks.size())
                .status("READY")
                .build();

        Document savedDoc = documentRepository.save(document);

        // Async insights generation (summary & suggested questions)
        String previewText = extractedText.substring(0, Math.min(extractedText.length(), 15000));
        CompletableFuture.runAsync(() -> generateInsights(savedDoc.getId(), previewText));

        return savedDoc;
    }

    @SuppressWarnings("unchecked")
    private void triggerAirflowDAG(Document doc) {
        try {
            org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
            headers.setContentType(org.springframework.http.MediaType.APPLICATION_JSON);
            headers.setBasicAuth("admin", "admin"); // Airflow default admin auth

            Map<String, Object> conf = new HashMap<>();
            conf.put("document_id", doc.getId());
            conf.put("file_path", doc.getFilePath());
            conf.put("file_name", doc.getFileName());
            conf.put("file_type", doc.getFileType());

            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("conf", conf);

            org.springframework.http.HttpEntity<Map<String, Object>> entity = new org.springframework.http.HttpEntity<>(requestBody, headers);
            String url = airflowApiUrl + "/dags/document_etl/dagRuns";

            log.info("Triggering Airflow DAG at: {}", url);
            org.springframework.http.ResponseEntity<Map> response = restTemplate.exchange(
                    url,
                    org.springframework.http.HttpMethod.POST,
                    entity,
                    Map.class
            );

            if (response.getStatusCode().is2xxSuccessful()) {
                log.info("Successfully triggered Airflow DAG for document ID: {}", doc.getId());
            } else {
                log.error("Failed to trigger Airflow DAG, status: {}", response.getStatusCode());
                updateDocumentStatus(doc.getId(), "FAILED");
            }
        } catch (Exception e) {
            log.error("Error triggering Airflow DAG: {}", e.getMessage(), e);
            updateDocumentStatus(doc.getId(), "FAILED");
        }
    }

    public void completeEtl(Long id, String vectorCollectionId, int chunkCount, String summary, String suggestedQuestions) {
        Optional<Document> docOpt = documentRepository.findById(id);
        if (docOpt.isPresent()) {
            Document doc = docOpt.get();
            doc.setVectorCollectionId(vectorCollectionId);
            doc.setChunkCount(chunkCount);
            doc.setSummary(summary);
            doc.setSuggestedQuestions(suggestedQuestions);
            doc.setStatus("READY");
            documentRepository.save(doc);
            log.info("Airflow ETL completed successfully for document ID: {}. State updated to READY.", id);
        } else {
            throw new RuntimeException("Document not found with ID: " + id);
        }
    }

    public void failEtl(Long id) {
        updateDocumentStatus(id, "FAILED");
        log.warn("Airflow ETL reported failure for document ID: {}. State updated to FAILED.", id);
    }

    private void updateDocumentStatus(Long id, String status) {
        try {
            Optional<Document> docOpt = documentRepository.findById(id);
            if (docOpt.isPresent()) {
                Document doc = docOpt.get();
                doc.setStatus(status);
                documentRepository.save(doc);
            }
        } catch (Exception e) {
            log.error("Error updating document status", e);
        }
    }

    @SuppressWarnings("unchecked")
    private void generateInsights(Long docId, String previewText) {
        try {
            log.info("Starting async insights generation for document ID: {}", docId);
            String prompt = "You are a professional document analyst. Analyze the following document text and generate two things:\n" +
                    "1. An Executive Summary: A concise high-level summary (3-5 bullet points) of the main topics and conclusions of the document.\n" +
                    "2. Suggested Questions: 5 highly relevant and insightful questions that a user would likely ask about this document.\n\n" +
                    "Return your response strictly in the following JSON format without any markdown wrapper (no ```json or ```):\n" +
                    "{\n" +
                    "  \"summary\": \"• Point 1\\n• Point 2\\n• Point 3\",\n" +
                    "  \"suggestedQuestions\": [\n" +
                    "    \"Question 1?\",\n" +
                    "    \"Question 2?\",\n" +
                    "    \"Question 3?\",\n" +
                    "    \"Question 4?\",\n" +
                    "    \"Question 5?\"\n" +
                    "  ]\n" +
                    "}\n\n" +
                    "Document Text:\n" + previewText;

            org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
            headers.setContentType(org.springframework.http.MediaType.APPLICATION_JSON);
            headers.setBearerAuth(openRouterConfig.getApiKey());

            List<Map<String, String>> messages = new ArrayList<>();
            messages.add(Map.of(
                    "role", "system",
                    "content", "You are a helpful assistant. Output ONLY valid JSON."
            ));
            messages.add(Map.of(
                    "role", "user",
                    "content", prompt
            ));

            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("model", openRouterConfig.getModel());
            requestBody.put("messages", messages);
            requestBody.put("temperature", 0.3); // Low temperature for high precision JSON
            requestBody.put("max_tokens", 1000);

            org.springframework.http.HttpEntity<Map<String, Object>> entity = new org.springframework.http.HttpEntity<>(requestBody, headers);

            org.springframework.http.ResponseEntity<Map> response = restTemplate.exchange(
                    openRouterConfig.getChatUrl(),
                    org.springframework.http.HttpMethod.POST,
                    entity,
                    Map.class
            );

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                List<Map<String, Object>> choices = (List<Map<String, Object>>) response.getBody().get("choices");
                if (choices != null && !choices.isEmpty()) {
                    Map<String, Object> firstChoice = choices.get(0);
                    Map<String, String> message = (Map<String, String>) firstChoice.get("message");
                    if (message != null) {
                        String jsonString = message.get("content");
                        // Clean markdown formatting if present
                        if (jsonString.contains("```")) {
                            jsonString = jsonString.replaceAll("```json|```", "").trim();
                        }

                        com.fasterxml.jackson.databind.JsonNode rootNode = objectMapper.readTree(jsonString);
                        String summary = rootNode.path("summary").asText();
                        com.fasterxml.jackson.databind.JsonNode questionsNode = rootNode.path("suggestedQuestions");
                        String questionsJson = objectMapper.writeValueAsString(questionsNode);

                        // Update document in database
                        Optional<Document> docOpt = documentRepository.findById(docId);
                        if (docOpt.isPresent()) {
                            Document doc = docOpt.get();
                            doc.setSummary(summary);
                            doc.setSuggestedQuestions(questionsJson);
                            documentRepository.save(doc);
                            log.info("Successfully saved async insights (summary & suggested questions) for document ID: {}", docId);
                            return;
                        }
                    }
                }
            }
            log.error("Failed to generate async insights for document ID: {}. Unexpected API response.", docId);
        } catch (Exception e) {
            log.error("Error generating insights for document ID: {}", docId, e);
        }
    }

    @SuppressWarnings("unchecked")
    public String getOrGenerateMindMap(Long id) {
        Document document = getDocumentById(id);
        if (document.getConceptMap() != null && !document.getConceptMap().isBlank()) {
            log.info("Returning cached mind map for document ID: {}", id);
            return document.getConceptMap();
        }

        log.info("Generating new mind map for document ID: {}", id);
        try {
            java.io.File file = new java.io.File(document.getFilePath());
            String extractedText = documentParser.extractText(file, document.getFileType());
            String previewText = extractedText.substring(0, Math.min(extractedText.length(), 15000));

            String prompt = "You are a professional knowledge analyst. Analyze the following document text and extract 8 to 12 main concepts/keywords. For each concept, provide:\n" +
                    "1. A short, concise label.\n" +
                    "2. A brief definition/description (1-2 sentences).\n" +
                    "3. Category/type of concept (e.g. Core, Financial, Technical, Process, Metric).\n" +
                    "Also, identify relationship lines (connections) between these concepts. Each relationship must link a source concept to a target concept with a short label.\n\n" +
                    "Return ONLY a valid JSON object in the following format without markdown blocks (no ```json or ```):\n" +
                    "{\n" +
                    "  \"nodes\": [\n" +
                    "    {\"id\": \"c1\", \"label\": \"Concept A\", \"description\": \"Description of A\", \"type\": \"Core\"},\n" +
                    "    {\"id\": \"c2\", \"label\": \"Concept B\", \"description\": \"Description of B\", \"type\": \"Sub\"}\n" +
                    "  ],\n" +
                    "  \"edges\": [\n" +
                    "    {\"source\": \"c1\", \"target\": \"c2\", \"label\": \"relates to\"}\n" +
                    "  ]\n" +
                    "}\n\n" +
                    "Document Text:\n" + previewText;

            org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
            headers.setContentType(org.springframework.http.MediaType.APPLICATION_JSON);
            headers.setBearerAuth(openRouterConfig.getApiKey());

            List<Map<String, String>> messages = new ArrayList<>();
            messages.add(Map.of(
                    "role", "system",
                    "content", "You are a helpful assistant. Output ONLY valid JSON."
            ));
            messages.add(Map.of(
                    "role", "user",
                    "content", prompt
            ));

            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("model", openRouterConfig.getModel());
            requestBody.put("messages", messages);
            requestBody.put("temperature", 0.3);
            requestBody.put("max_tokens", 1500);

            org.springframework.http.HttpEntity<Map<String, Object>> entity = new org.springframework.http.HttpEntity<>(requestBody, headers);

            org.springframework.http.ResponseEntity<Map> response = restTemplate.exchange(
                    openRouterConfig.getChatUrl(),
                    org.springframework.http.HttpMethod.POST,
                    entity,
                    Map.class
            );

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                List<Map<String, Object>> choices = (List<Map<String, Object>>) response.getBody().get("choices");
                if (choices != null && !choices.isEmpty()) {
                    Map<String, Object> firstChoice = choices.get(0);
                    Map<String, String> message = (Map<String, String>) firstChoice.get("message");
                    if (message != null) {
                        String jsonString = message.get("content");
                        if (jsonString.contains("```")) {
                            jsonString = jsonString.replaceAll("```json|```", "").trim();
                        }

                        // Validate JSON parsing
                        objectMapper.readTree(jsonString);

                        // Save to cache
                        document.setConceptMap(jsonString);
                        documentRepository.save(document);

                        log.info("Successfully generated and cached mind map for document ID: {}", id);
                        return jsonString;
                    }
                }
            }
        } catch (Exception e) {
            log.error("Error generating mind map for document ID: {}", id, e);
        }
        return null;
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
