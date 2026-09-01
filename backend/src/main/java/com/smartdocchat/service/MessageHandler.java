package com.smartdocchat.service;

import com.smartdocchat.util.LlmConfig;
import com.smartdocchat.metrics.RagMetrics;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

@Service
@RequiredArgsConstructor
@Slf4j
public class MessageHandler {

    private final LlmConfig llmConfig;
    private final RestTemplate restTemplate;
    private final RagMetrics ragMetrics;
    private final LlmClient llmClient;
    private final ObjectMapper objectMapper = new ObjectMapper();
    @org.springframework.beans.factory.annotation.Value("${security.internal-token:}")
    private String internalToken;

    private static final String DEFAULT_SYSTEM_PROMPT = """
            Bạn là trợ lý pháp luật Việt Nam. NHIỆM VỤ: Trả lời câu hỏi DỰA TRÊN nội dung tài liệu được cung cấp.

            QUY TẮC BẮT BUỘC:
            1. CHỈ sử dụng thông tin trong phần [TÀI LIỆU] bên dưới
            2. TRÍCH DẪN chính xác: số Điều, khoản, nội dung cụ thể
            3. PHẢI nêu rõ các thuật ngữ pháp lý quan trọng (ví dụ: "tư nhân", "cổ phần", "trách nhiệm hữu hạn")
            4. Nếu tài liệu không có thông tin → trả lời: "Không tìm thấy thông tin trong tài liệu."
            5. KHÔNG đoán, KHÔNG bịa định, KHÔNG dùng kiến thức bên ngoài

            VÍ DỤ TRẢ LỜI ĐÚNG:
            "Theo Điều 7 Luật Doanh nghiệp 2020, hình thức doanh nghiệp bao gồm:
            (1) Doanh nghiệp tư nhân - do một cá nhân làm chủ;
            (2) Công ty trách nhiệm hữu hạn - thành viên chịu trách nhiệm trong phạm vi vốn góp;
            (3) Công ty cổ phần - vốn được chia thành các cổ phần."

            VÍ DỤ TRẢ LỜI SAI (KHÔNG ĐƯỢC):
            "Điều 7 quy định về hình thức doanh nghiệp." (thiếu chi tiết, thiếu thuật ngữ)
            """;

    private static final String CITATION_REQUIREMENT = """

            ═══════════════════════════════════════════════════════
            NHẮC LẠI QUY TẮC:
            - PHẢI trích dẫn Điều/Khoản cụ thể
            - PHẢI nêu rõ các thuật ngữ pháp lý từ tài liệu
            - KHÔNG trả lời chung chung, thiếu chi tiết
            ═══════════════════════════════════════════════════════""";

    public String buildPrompt(String userQuestion, List<String> relevantChunks) {
        StringBuilder prompt = new StringBuilder();
        prompt.append(DEFAULT_SYSTEM_PROMPT);
        prompt.append("\n\n[TÀI LIỆU]\n");

        if (relevantChunks != null && !relevantChunks.isEmpty()) {
            for (int i = 0; i < relevantChunks.size(); i++) {
                prompt.append("[").append(i + 1).append("] ").append(relevantChunks.get(i)).append("\n\n");
            }
        } else {
            prompt.append("(Không tìm thấy tài liệu liên quan)\n");
        }

        prompt.append("[/TÀI LIỆU]\n\n");
        prompt.append("CÂU HỎI: ").append(userQuestion).append("\n\n");
        prompt.append("TRẢ LỜI (phải trích dẫn Điều/Khoản và nêu rõ thuật ngữ pháp lý):");
        prompt.append(CITATION_REQUIREMENT);
        return prompt.toString();
    }

    public String buildGeneralKnowledgePrompt(String userQuestion) {
        return DEFAULT_SYSTEM_PROMPT + """

                [TÀI LIỆU]
                (Không tìm thấy tài liệu liên quan trong hệ thống)
                [/TÀI LIỆU]

                CÂU HỎI: """ + userQuestion + """

                TRẢ LỜI: Không tìm thấy thông tin trong tài liệu. Vui lòng tải lên tài liệu liên quan.""";
    }

    public String buildWebSearchPrompt(String userQuestion, List<String> snippets) {
        StringBuilder prompt = new StringBuilder();
        prompt.append(DEFAULT_SYSTEM_PROMPT);
        prompt.append("\n\n[KẾT QUẌA TÌM KIẾM WEB]\n");

        if (snippets != null) {
            for (int i = 0; i < snippets.size(); i++) {
                prompt.append("[").append(i + 1).append("] ").append(snippets.get(i)).append("\n\n");
            }
        }

        prompt.append("[/KẾT QUẌA TÌM KIẾM WEB]\n\n");
        prompt.append("CÂU HỎI: ").append(userQuestion).append("\n\n");
        prompt.append("TRẢ LỜI (phải trích dẫn nguồn [1], [2]... và nêu rõ thuật ngữ):");
        prompt.append(CITATION_REQUIREMENT);
        return prompt.toString();
    }

    public String buildAbstentionResponse() {
        return "Không tìm thấy thông tin trong tài liệu để trả lời câu hỏi này. "
             + "Vui lòng: (1) Đổi từ khóa tìm kiếm, hoặc (2) Tải lên tài liệu liên quan.";
    }

    public String buildInjectionBlockedResponse() {
        return "I can't process this request: it appears to contain instructions that attempt to "
                + "override the assistant's behavior. Please rephrase your question in a normal way.";
    }

    private static final int MAX_CACHE_SIZE = 100;
    private final Map<String, String> responseCache = Collections.synchronizedMap(
            new LinkedHashMap<>(MAX_CACHE_SIZE, 0.75f, true) {
                @Override
                protected boolean removeEldestEntry(Map.Entry<String, String> eldest) {
                    return size() > MAX_CACHE_SIZE;
                }
            });

    public String callLLM(String prompt) {
        return callLLM(DEFAULT_SYSTEM_PROMPT, prompt);
    }

    public String callLLM(String systemPrompt, String userPrompt) {
        String cacheKey = systemPrompt + "|||" + userPrompt;
        String cached = responseCache.get(cacheKey);
        if (cached != null) {
            log.debug("Cache hit for LLM query");
            return cached;
        }

        String result = null;
        int maxAttempts = llmConfig.getMaxAttempts();
        long backoff = llmConfig.getRetryBackoffMs();

        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            result = callLLMOnce(systemPrompt, userPrompt);
            if (!result.startsWith("Sorry, the language model is temporarily unavailable.")
                    && !result.startsWith("Sorry, I could not generate a response.")) {
                responseCache.put(cacheKey, result);
                return result;
            }
            if (attempt < maxAttempts) {
                try {
                    Thread.sleep(backoff * attempt);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    return result;
                }
            }
        }
        return result;
    }

    @Cacheable(value = "llmCache", key = "#systemPrompt.hashCode() + '|||' + #userPrompt.hashCode()")
    public String callLLMCached(String systemPrompt, String userPrompt) {
        log.debug("Cache miss for LLM call");
        return callLLM(systemPrompt, userPrompt);
    }

    public String callLLMOnce(String prompt) {
        return callLLMOnce(DEFAULT_SYSTEM_PROMPT, prompt);
    }

    public String callLLMOnce(String systemPrompt, String userPrompt) {
        return llmClient.chat(systemPrompt, userPrompt);
    }

    public void streamLLM(String prompt, Consumer<String> onToken) {
        streamLLM(DEFAULT_SYSTEM_PROMPT, prompt, onToken);
    }

    public void streamLLM(String systemPrompt, String userPrompt, Consumer<String> onToken) {
        restTemplate.execute(llmConfig.getChatUrl(), HttpMethod.POST, request -> {
            request.getHeaders().setContentType(MediaType.APPLICATION_JSON);
            if (internalToken != null && !internalToken.isBlank()) {
                request.getHeaders().set("X-Internal-Token", internalToken);
            }
            objectMapper.writeValue(request.getBody(), buildChatRequest(systemPrompt, userPrompt, true));
        }, response -> {
            if (!response.getStatusCode().is2xxSuccessful()) {
                throw new IllegalStateException("LLM stream request failed: " + response.getStatusCode());
            }
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(response.getBody(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    JsonNode message = objectMapper.readTree(line).path("message");
                    String token = message.path("content").asText("");
                    if (!token.isEmpty()) {
                        onToken.accept(token);
                    }
                }
            }
            return null;
        });
    }

    private Map<String, Object> buildChatRequest(String systemPrompt, String userPrompt, boolean stream) {
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("model", llmConfig.getChatModel());
        requestBody.put("messages", List.of(
                Map.of("role", "system", "content", systemPrompt),
                Map.of("role", "user", "content", userPrompt)));
        requestBody.put("options",
                Map.of("temperature", llmConfig.getTemperature(), "top_p", llmConfig.getTopP(), "num_predict", 2048));
        requestBody.put("stream", stream);
        return requestBody;
    }
}
