package com.smartdocchat.observability;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.annotation.PreDestroy;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentLinkedQueue;

/**
 * Opt-in bridge to Langfuse via the stable public ingestion API
 * (POST /api/public/ingestion). Every public method is a no-op when the
 * tracer is disabled (no {@code LANGFUSE_PUBLIC_KEY}), so the rest of the
 * app can call it unconditionally with zero overhead.
 *
 * A single CRAG request = one trace. The trace id is stored in a thread-local
 * so it can be propagated to the FastAPI llm-router as the
 * {@code X-Langfuse-Trace-Id} header, producing one continuous tree across
 * the Java and Python tiers (Phase 2 glue).
 *
 * Events are buffered per-request and flushed at the end of the request so a
 * parent span always exists before its children reference it.
 */
@Service
public class LangfuseService {

    private static final Logger log = LoggerFactory.getLogger(LangfuseService.class);

    private final boolean enabled;
    private final String host;
    private final String publicKey;
    private final String secretKey;
    private final String routerTraceHeader;

    private final ThreadLocal<TraceContext> ctx = new ThreadLocal<>();
    private final ObjectMapper mapper = new ObjectMapper();
    private final HttpClient http;

    public LangfuseService(
            @Value("${langfuse.enabled:true}") boolean enabled,
            @Value("${langfuse.host:https://cloud.langfuse.com}") String host,
            @Value("${langfuse.public-key:}") String publicKey,
            @Value("${langfuse.secret-key:}") String secretKey,
            @Value("${langfuse.router-trace-header:X-Langfuse-Trace-Id}") String routerTraceHeader) {
        this.enabled = enabled && publicKey != null && !publicKey.isBlank()
                && secretKey != null && !secretKey.isBlank();
        this.host = host.endsWith("/") ? host.substring(0, host.length() - 1) : host;
        this.publicKey = publicKey;
        this.secretKey = secretKey;
        this.routerTraceHeader = routerTraceHeader;
        this.http = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        if (!this.enabled) {
            log.info("Langfuse tracing disabled (no keys / enabled=false)");
        }
    }

    /** No-arg constructor: tracing disabled (used in tests). */
    public LangfuseService() {
        this.enabled = false;
        this.host = "https://cloud.langfuse.com";
        this.publicKey = "";
        this.secretKey = "";
        this.routerTraceHeader = "X-Langfuse-Trace-Id";
        this.http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
    }

    public boolean isEnabled() {
        return enabled;
    }

    /** Begin a request-level trace. Returns the trace id for cross-tier propagation. */
    public String startTrace(String name, String userId, Map<String, Object> input) {
        if (!enabled) {
            return null;
        }
        String traceId = "trace-" + UUID.randomUUID();
        ctx.set(new TraceContext(traceId, name, userId, input));
        return traceId;
    }

    /** Open a child span under the current trace. Returns the event/span id. */
    public String startSpan(String name, Map<String, Object> input) {
        TraceContext tc = ctx.get();
        if (!enabled || tc == null) {
            return null;
        }
        String spanId = "span-" + UUID.randomUUID();
        tc.events.add(ingestEvent("span-create", Map.of(
                "id", spanId,
                "traceId", tc.traceId,
                "parentObservationId", tc.currentParent,
                "name", name,
                "startTime", now(),
                "input", input == null ? Map.of() : input
        )));
        return spanId;
    }

    /** Close a span, attaching output + metadata attributes. */
    public void endSpan(String spanId, String output, Map<String, Object> attributes) {
        TraceContext tc = ctx.get();
        if (!enabled || tc == null || spanId == null) {
            return;
        }
        Map<String, Object> body = new HashMap<>();
        body.put("id", spanId);
        body.put("traceId", tc.traceId);
        body.put("endTime", now());
        body.put("output", output == null ? "" : output);
        if (attributes != null && !attributes.isEmpty()) {
            body.put("metadata", attributes);
        }
        tc.events.add(ingestEvent("span-update", body));
    }

    /** Open a generation (LLM call) under the current trace. */
    public String startGeneration(String name, String model, Map<String, Object> input) {
        TraceContext tc = ctx.get();
        if (!enabled || tc == null) {
            return null;
        }
        String genId = "gen-" + UUID.randomUUID();
        Map<String, Object> body = new HashMap<>();
        body.put("id", genId);
        body.put("traceId", tc.traceId);
        if (tc.currentParent != null) {
            body.put("parentObservationId", tc.currentParent);
        }
        body.put("name", name);
        body.put("model", model);
        body.put("startTime", now());
        body.put("input", input == null ? List.of() : input);
        tc.events.add(ingestEvent("generation-create", body));
        return genId;
    }

    /** End a generation, attaching output + token usage. */
    public void endGeneration(String genId, String output, Long outputTokens) {
        TraceContext tc = ctx.get();
        if (!enabled || tc == null || genId == null) {
            return;
        }
        Map<String, Object> body = new HashMap<>();
        body.put("id", genId);
        body.put("traceId", tc.traceId);
        body.put("endTime", now());
        body.put("output", output == null ? "" : output);
        if (outputTokens != null) {
            body.put("usage", Map.of("input", 0, "output", outputTokens, "unit", "TOKENS"));
        }
        tc.events.add(ingestEvent("generation-update", body));
    }

    /** Push the trace-level metadata/attributes (strategy, confidence, tokens, ...). */
    public void updateTrace(Map<String, Object> metadata, Map<String, Object> output) {
        TraceContext tc = ctx.get();
        if (!enabled || tc == null) {
            return;
        }
        tc.traceMeta.putAll(metadata == null ? Map.of() : metadata);
        if (output != null) {
            tc.traceOutput = output;
        }
    }

    /** Header map carrying the current trace id to the llm-router (Phase 2 glue). */
    public Map<String, String> routerTraceHeaders() {
        Map<String, String> headers = new HashMap<>();
        TraceContext tc = ctx.get();
        if (tc != null && routerTraceHeader != null && !routerTraceHeader.isBlank()) {
            headers.put(routerTraceHeader, tc.traceId);
        }
        return headers;
    }

    /** Set the active parent observation id for nested spans (advanced use). */
    public void setCurrentParent(String observationId) {
        TraceContext tc = ctx.get();
        if (tc != null) {
            tc.currentParent = observationId;
        }
    }

    /** Flush the buffered events to Langfuse and clear the thread-local. */
    public void flush() {
        TraceContext tc = ctx.get();
        if (!enabled || tc == null) {
            ctx.remove();
            return;
        }
        try {
            // 1) trace-create first
            List<Map<String, Object>> batch = new ArrayList<>();
            Map<String, Object> traceBody = new HashMap<>();
            traceBody.put("id", tc.traceId);
            traceBody.put("name", tc.name);
            if (tc.userId != null) {
                traceBody.put("userId", tc.userId);
            }
            traceBody.put("input", tc.input == null ? Map.of() : tc.input);
            if (!tc.traceMeta.isEmpty()) {
                traceBody.put("metadata", tc.traceMeta);
            }
            if (tc.traceOutput != null) {
                traceBody.put("output", tc.traceOutput);
            }
            batch.add(ingestEvent("trace-create", traceBody));
            batch.addAll(tc.events);
            post(batch);
        } catch (Exception e) {
            log.debug("Langfuse flush error: {}", e.getMessage());
        } finally {
            ctx.remove();
        }
    }

    /** Clear without flushing (e.g. on unexpected error paths). */
    public void clear() {
        ctx.remove();
    }

    private Map<String, Object> ingestEvent(String type, Object body) {
        Map<String, Object> ev = new HashMap<>();
        ev.put("id", UUID.randomUUID().toString());
        ev.put("type", type);
        ev.put("timestamp", now());
        ev.put("body", body);
        return ev;
    }

    private String now() {
        return Instant.now().toString().replace("+00:00", "Z");
    }

    private void post(List<Map<String, Object>> batch) throws Exception {
        Map<String, Object> payload = Map.of("batch", batch);
        String json = mapper.writeValueAsString(payload);
        HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(host + "/api/public/ingestion"))
                .timeout(Duration.ofSeconds(10))
                .header("Content-Type", "application/json")
                .header("Authorization",
                        "Basic " + java.util.Base64.getEncoder()
                                .encodeToString((publicKey + ":" + secretKey).getBytes()))
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .build();
        http.send(req, HttpResponse.BodyHandlers.ofString());
    }

    /** Per-request buffer of Langfuse ingestion events. */
    private static final class TraceContext {
        final String traceId;
        final String name;
        final String userId;
        final Map<String, Object> input;
        final List<Map<String, Object>> events = new ArrayList<>();
        final Map<String, Object> traceMeta = new java.util.concurrent.ConcurrentHashMap<>();
        Map<String, Object> traceOutput;
        String currentParent;

        TraceContext(String traceId, String name, String userId, Map<String, Object> input) {
            this.traceId = traceId;
            this.name = name;
            this.userId = userId;
            this.input = input;
        }
    }

    @PreDestroy
    public void shutdown() {
        // best-effort: pending thread-locals are flushed per-request
    }
}
