package com.smartdocchat.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartdocchat.dto.ChatRequest;
import com.smartdocchat.entity.ChatMessage;
import com.smartdocchat.service.ChatService;
import com.smartdocchat.util.JwtTokenProvider;
import com.smartdocchat.config.JwtAuthenticationFilter;
import com.smartdocchat.config.RateLimitingFilter;
import com.smartdocchat.config.InternalServiceAuthenticationFilter;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(ChatController.class)
@AutoConfigureMockMvc
public class ChatControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ChatService chatService;

    @MockBean
    private JwtTokenProvider jwtTokenProvider;

    @MockBean
    private JwtAuthenticationFilter jwtAuthenticationFilter;

    @MockBean
    private RateLimitingFilter rateLimitingFilter;

    @MockBean
    private InternalServiceAuthenticationFilter internalServiceAuthenticationFilter;

    @Autowired
    private ObjectMapper objectMapper;

    @Test
    @WithMockUser(username = "testuser", roles = {"USER"})
    public void testAskQuestion_Success() throws Exception {
        ChatRequest request = ChatRequest.builder()
                .sessionId("session-abc")
                .documentId(1L)
                .message("Hello")
                .build();

        ChatMessage message = ChatMessage.builder()
                .id(1L)
                .sessionId("session-abc")
                .documentId(1L)
                .userMessage("Hello")
                .aiResponse("Hi there")
                .build();

        Mockito.when(chatService.processQuery(eq("testuser"), anyString(), anyLong(), any(), anyString()))
                .thenReturn(message);

        mockMvc.perform(post("/chat/ask")
                        .with(csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.aiResponse").value("Hi there"));
    }

    @Test
    @WithMockUser(username = "testuser", roles = {"USER"})
    public void testAskQuestion_ValidationFailure() throws Exception {
        // ChatRequest with empty message and session ID should trigger validation errors
        ChatRequest request = ChatRequest.builder()
                .sessionId("")
                .message("")
                .build();

        mockMvc.perform(post("/chat/ask")
                        .with(csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest());
    }
}
