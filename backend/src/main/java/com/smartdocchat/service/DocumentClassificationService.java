package com.smartdocchat.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * Gọi llm-router để phân loại loại tài liệu (PO / Invoice / ASN / Other).
 * Dùng Nous model (llama-3.3-70b) chạy trên llm-router-python.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class DocumentClassificationService {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${llm-router.base-url:http://localhost:8010}")
    private String llmRouterBaseUrl;

    /**
     * Phân loại tài liệu dựa trên nội dung text đã extract.
     *
     * @param documentText nội dung text của tài liệu
     * @param fileName    tên file gốc
     * @return documentType: "PO", "INVOICE", "ASN", "OTHER"
     */
    public String classifyDocument(String documentText, String fileName) {
        try {
            // Gọi llm-router endpoint /classify
            String url = llmRouterBaseUrl + "/classify";
            Map<String, String> requestBody = Map.of(
                    "text", documentText.length() > 4000 ? documentText.substring(0, 4000) : documentText,
                    "filename", fileName
            );

            ResponseEntity<Map> response = restTemplate.postForEntity(url, requestBody, Map.class);

            if (response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                String docType = (String) response.getBody().get("document_type");
                if (docType != null && !docType.isBlank()) {
                    log.info("Document '{}' classified as: {}", fileName, docType);
                    return docType.toUpperCase();
                }
            }
        } catch (Exception e) {
            log.warn("Classification service call failed, falling back to heuristic: {}", e.getMessage());
        }

        // Fallback heuristic: dựa trên từ khóa trong text
        return classifyHeuristic(documentText, fileName);
    }

    /**
     * Fallback heuristic classification khi llm-router không available.
     */
    private String classifyHeuristic(String text, String fileName) {
        String lower = text.toLowerCase();

        // Purchase Order indicators
        if (lower.contains("purchase order") || lower.contains("đơn đặt hàng") ||
                lower.contains("po #") || lower.contains("po number") ||
                lower.contains("số đặt hàng") || lower.contains("đặt hàng")) {
            return "PO";
        }

        // Invoice indicators
        if (lower.contains("invoice") || lower.contains("hóa đơn") ||
                lower.contains("inv #") || lower.contains("số hóa đơn") ||
                lower.contains("số inv") || lower.contains("tổng cộng") && lower.contains("thành tiền")) {
            return "INVOICE";
        }

        // ASN (Advanced Shipping Notice) indicators
        if (lower.contains("asn") || lower.contains("advanced shipping notice") ||
                lower.contains("lưu ý vận chuyển") || lower.contains("ship notice") ||
                lower.contains("đón hàng") || lower.contains("ngày dự kiến giao")) {
            return "ASN";
        }

        // Heuristic based on filename
        String lowerName = fileName.toLowerCase();
        if (lowerName.contains("po") || lowerName.contains("đặt")) {
            return "PO";
        }
        if (lowerName.contains("inv") || lowerName.contains("hóa đơn") || lowerName.contains("invoice")) {
            return "INVOICE";
        }
        if (lowerName.contains("asn") || lowerName.contains("ship") || lowerName.contains("vận chuyển")) {
            return "ASN";
        }

        return "OTHER";
    }
}
