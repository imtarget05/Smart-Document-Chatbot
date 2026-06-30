package com.smartdocchat.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.file.*;

/**
 * StorageService — abstraction over file storage backends.
 *
 * <p>Two providers are supported, selected by {@code STORAGE_PROVIDER} env var:
 * <ul>
 *   <li><b>local</b> — writes to {@code uploads/} on the local filesystem (dev/test)</li>
 *   <li><b>supabase</b> — uploads to Supabase Storage via REST API (production, free 1 GB tier)</li>
 * </ul>
 *
 * <p>Supabase Storage REST API docs:
 * <a href="https://supabase.com/docs/reference/api/storage">storage reference</a>
 */
@Service
@Slf4j
public class StorageService {

    private final RestTemplate restTemplate;

    @Value("${storage.provider:local}")
    private String provider;

    // ── Supabase config ───────────────────────────────────────────────────────
    @Value("${storage.supabase.url:}")
    private String supabaseUrl;

    @Value("${storage.supabase.bucket:documents}")
    private String supabaseBucket;

    @Value("${storage.supabase.service-key:}")
    private String supabaseServiceKey;

    // ── Local config ──────────────────────────────────────────────────────────
    @Value("${storage.local.upload-dir:uploads}")
    private String localUploadDir;

    public StorageService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    // -----------------------------------------------------------------------
    // Public API
    // -----------------------------------------------------------------------

    /**
     * Store the given file and return an opaque storage path/key.
     * The returned value must be passed back to {@link #download} and {@link #delete}.
     *
     * @param fileName  final filename (UUID-based, already sanitized)
     * @param file      multipart file from HTTP request
     * @return storage key (local relative path OR Supabase object path)
     */
    public String upload(String fileName, MultipartFile file) throws IOException {
        if ("supabase".equalsIgnoreCase(provider)) {
            return uploadToSupabase(fileName, file.getBytes(), file.getContentType());
        }
        return uploadToLocal(fileName, file.getBytes());
    }

    /**
     * Download the file content as a {@link File} for in-process parsing.
     * Callers must delete the temp file when done.
     */
    public File download(String storagePath) throws IOException {
        if ("supabase".equalsIgnoreCase(provider)) {
            return downloadFromSupabase(storagePath);
        }
        return downloadFromLocal(storagePath);
    }

    /**
     * Delete the stored file.
     */
    public void delete(String storagePath) {
        if ("supabase".equalsIgnoreCase(provider)) {
            deleteFromSupabase(storagePath);
        } else {
            deleteFromLocal(storagePath);
        }
    }

    // -----------------------------------------------------------------------
    // Local filesystem implementation
    // -----------------------------------------------------------------------

    private String uploadToLocal(String fileName, byte[] bytes) throws IOException {
        Path dir = Paths.get(localUploadDir);
        Files.createDirectories(dir);
        Path target = dir.resolve(fileName);
        Files.write(target, bytes);
        log.info("Saved file locally: {}", target);
        return target.toString();
    }

    private File downloadFromLocal(String storagePath) {
        return new File(storagePath);
    }

    private void deleteFromLocal(String storagePath) {
        try {
            Files.deleteIfExists(Paths.get(storagePath));
            log.info("Deleted local file: {}", storagePath);
        } catch (IOException e) {
            log.error("Failed to delete local file: {}", storagePath, e);
        }
    }

    // -----------------------------------------------------------------------
    // Supabase Storage REST API implementation
    // -----------------------------------------------------------------------

    /**
     * Upload object to Supabase Storage.
     * POST /storage/v1/object/{bucket}/{fileName}
     *
     * @return Supabase object path (e.g. "documents/uuid.pdf")
     */
    private String uploadToSupabase(String fileName, byte[] bytes, String contentType) {
        String objectPath = supabaseBucket + "/" + fileName;
        String url = supabaseUrl + "/storage/v1/object/" + objectPath;

        HttpHeaders headers = buildSupabaseHeaders();
        headers.setContentType(
                contentType != null ? MediaType.parseMediaType(contentType) : MediaType.APPLICATION_OCTET_STREAM
        );

        HttpEntity<byte[]> entity = new HttpEntity<>(bytes, headers);

        try {
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, entity, String.class);
            if (response.getStatusCode().is2xxSuccessful()) {
                log.info("Uploaded to Supabase Storage: {}", objectPath);
                return objectPath;
            }
            throw new IOException("Supabase upload failed: " + response.getStatusCode());
        } catch (Exception e) {
            log.error("Error uploading to Supabase: {}", e.getMessage(), e);
            throw new RuntimeException("Storage upload failed", e);
        }
    }

    /**
     * Download object from Supabase Storage to a temp file.
     * GET /storage/v1/object/{objectPath}
     */
    private File downloadFromSupabase(String objectPath) throws IOException {
        String url = supabaseUrl + "/storage/v1/object/" + objectPath;

        HttpHeaders headers = buildSupabaseHeaders();
        HttpEntity<Void> entity = new HttpEntity<>(headers);

        try {
            ResponseEntity<byte[]> response = restTemplate.exchange(url, HttpMethod.GET, entity, byte[].class);
            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                // Write to a temp file so existing parsers (PDFBox, POI) can read it
                String extension = objectPath.contains(".") ? objectPath.substring(objectPath.lastIndexOf('.')) : ".tmp";
                File tempFile = File.createTempFile("sdc_download_", extension);
                tempFile.deleteOnExit();
                Files.write(tempFile.toPath(), response.getBody());
                log.info("Downloaded {} bytes from Supabase: {}", response.getBody().length, objectPath);
                return tempFile;
            }
            throw new IOException("Supabase download returned: " + response.getStatusCode());
        } catch (Exception e) {
            log.error("Error downloading from Supabase: {}", e.getMessage(), e);
            throw new IOException("Storage download failed: " + e.getMessage(), e);
        }
    }

    /**
     * Delete object from Supabase Storage.
     * DELETE /storage/v1/object/{bucket}?prefixes={fileName}
     */
    private void deleteFromSupabase(String objectPath) {
        // objectPath = "documents/uuid.pdf" — extract just the filename part
        String fileName = objectPath.contains("/") ? objectPath.substring(objectPath.indexOf('/') + 1) : objectPath;
        String url = supabaseUrl + "/storage/v1/object/" + supabaseBucket + "?prefixes=" + fileName;

        HttpHeaders headers = buildSupabaseHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        // Supabase delete requires body with "prefixes" array
        String body = "{\"prefixes\":[\"" + fileName + "\"]}";
        HttpEntity<String> entity = new HttpEntity<>(body, headers);

        try {
            restTemplate.exchange(url, HttpMethod.DELETE, entity, String.class);
            log.info("Deleted from Supabase Storage: {}", objectPath);
        } catch (Exception e) {
            log.error("Error deleting from Supabase: {}", e.getMessage(), e);
        }
    }

    private HttpHeaders buildSupabaseHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.set("Authorization", "Bearer " + supabaseServiceKey);
        headers.set("apikey", supabaseServiceKey);
        return headers;
    }
}
