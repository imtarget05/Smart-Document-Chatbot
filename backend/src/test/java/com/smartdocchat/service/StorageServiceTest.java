package com.smartdocchat.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestTemplate;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class StorageServiceTest {

    @Mock private RestTemplate restTemplate;

    private StorageService storageService;

    @BeforeEach
    void setUp() {
        storageService = new StorageService(restTemplate);
        ReflectionTestUtils.setField(storageService, "provider", "local");
    }

    @Test
    void localUploadDownloadDeleteCycle(@org.junit.jupiter.api.io.TempDir Path tempDir) throws Exception {
        ReflectionTestUtils.setField(storageService, "localUploadDir", tempDir.toString());

        MockMultipartFile file = new MockMultipartFile(
                "file", "doc.txt", "text/plain", "content".getBytes(StandardCharsets.UTF_8));
        String path = storageService.upload("doc.txt", file);

        assertTrue(path.contains("doc.txt"));
        assertTrue(Files.exists(Path.of(path)));

        File downloaded = storageService.download(path);
        assertEquals("content", new String(Files.readAllBytes(downloaded.toPath()), StandardCharsets.UTF_8));

        storageService.delete(path);
        assertTrue(!Files.exists(Path.of(path)));
        storageService.delete(path);
    }

    @Test
    void supabaseUploadBuildsObjectPath() throws Exception {
        ReflectionTestUtils.setField(storageService, "provider", "supabase");
        ReflectionTestUtils.setField(storageService, "supabaseUrl", "https://xyz.supabase.co");
        ReflectionTestUtils.setField(storageService, "supabaseBucket", "documents");
        ReflectionTestUtils.setField(storageService, "supabaseServiceKey", "service-key");

        when(restTemplate.exchange(eq("https://xyz.supabase.co/storage/v1/object/documents/uuid.pdf"),
                eq(HttpMethod.POST), any(), eq(String.class)))
                .thenReturn(ResponseEntity.ok("{}"));

        MockMultipartFile file = new MockMultipartFile(
                "file", "doc.pdf", "application/pdf", "content".getBytes());
        assertEquals("documents/uuid.pdf", storageService.upload("uuid.pdf", file));
    }

    @Test
    void supabaseUploadThrowsOnFailureOrException() {
        ReflectionTestUtils.setField(storageService, "provider", "supabase");
        ReflectionTestUtils.setField(storageService, "supabaseUrl", "https://xyz.supabase.co");
        ReflectionTestUtils.setField(storageService, "supabaseBucket", "documents");

        when(restTemplate.exchange(any(String.class), eq(HttpMethod.POST), any(), eq(String.class)))
                .thenReturn(ResponseEntity.status(HttpStatus.BAD_REQUEST).body("{}"));
        MockMultipartFile file = new MockMultipartFile("file", "doc.pdf", "application/pdf", "c".getBytes());
        assertThrows(RuntimeException.class, () -> storageService.upload("uuid.pdf", file));
    }

    @Test
    void supabaseDownloadWritesTempFileWithOwnerOnlyPermissions() throws Exception {
        ReflectionTestUtils.setField(storageService, "provider", "supabase");
        ReflectionTestUtils.setField(storageService, "supabaseUrl", "https://xyz.supabase.co");
        ReflectionTestUtils.setField(storageService, "supabaseBucket", "documents");
        ReflectionTestUtils.setField(storageService, "supabaseServiceKey", "k");

        when(restTemplate.exchange(eq("https://xyz.supabase.co/storage/v1/object/documents/uuid.pdf"),
                eq(HttpMethod.GET), any(), eq(byte[].class)))
                .thenReturn(ResponseEntity.ok("bytes".getBytes(StandardCharsets.UTF_8)));

        File file = storageService.download("documents/uuid.pdf");

        assertTrue(file.getName().contains("sdc_download_"));
        assertEquals("bytes", new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8));
    }

    @Test
    void supabaseDownloadThrowsOnNon2xx() {
        ReflectionTestUtils.setField(storageService, "provider", "supabase");
        ReflectionTestUtils.setField(storageService, "supabaseUrl", "https://xyz.supabase.co");
        ReflectionTestUtils.setField(storageService, "supabaseBucket", "documents");

        when(restTemplate.exchange(any(String.class), eq(HttpMethod.GET), any(), eq(byte[].class)))
                .thenReturn(ResponseEntity.status(HttpStatus.NOT_FOUND).body(null));

        assertThrows(java.io.IOException.class, () -> storageService.download("documents/uuid.pdf"));
    }

    @Test
    void supabaseDeleteSendsPrefixedRequestAndSwallowsErrors() {
        ReflectionTestUtils.setField(storageService, "provider", "supabase");
        ReflectionTestUtils.setField(storageService, "supabaseUrl", "https://xyz.supabase.co");
        ReflectionTestUtils.setField(storageService, "supabaseBucket", "documents");

        doThrow(new RuntimeException("gone")).when(restTemplate)
                .exchange(any(String.class), eq(HttpMethod.DELETE), any(), eq(String.class));
        storageService.delete("documents2/uuid.pdf");

        verify(restTemplate).exchange(eq("https://xyz.supabase.co/storage/v1/object/documents?prefixes=uuid.pdf"),
                eq(HttpMethod.DELETE), any(), eq(String.class));
    }
}