package com.smartdocchat.exception;

import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.validation.BeanPropertyBindingResult;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class GlobalExceptionHandlerTest {

    private GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @Test
    void maxUploadSizeReturnsPayloadTooLarge() {
        ResponseEntity<Map<String, String>> response =
                handler.handleMaxUploadSizeException(new MaxUploadSizeExceededException(50L * 1024 * 1024));
        assertEquals(HttpStatus.PAYLOAD_TOO_LARGE, response.getStatusCode());
        assertEquals("File size exceeds maximum limit of 50MB", response.getBody().get("error"));
    }

    @Test
    void validationExceptionCollectsFieldErrors() {
        MethodArgumentNotValidException e = mock(MethodArgumentNotValidException.class);
        BeanPropertyBindingResult bindingResult = new BeanPropertyBindingResult(new Object(), "obj");
        bindingResult.addError(new FieldError("obj", "username", "Username must not be blank"));
        bindingResult.addError(new FieldError("obj", "password", "Password must not be blank"));
        when(e.getBindingResult()).thenReturn(bindingResult);

        ResponseEntity<Map<String, String>> response = handler.handleValidationException(e);

        assertEquals(HttpStatus.BAD_REQUEST, response.getStatusCode());
        assertEquals("Username must not be blank", response.getBody().get("username"));
        assertEquals("Password must not be blank", response.getBody().get("password"));
    }

    @Test
    void accessDeniedReturnsForbidden() {
        ResponseEntity<Map<String, String>> response =
                handler.handleAccessDeniedException(new AccessDeniedException("denied"));
        assertEquals(HttpStatus.FORBIDDEN, response.getStatusCode());
        assertEquals("Access denied. You do not have sufficient permissions.", response.getBody().get("error"));
    }

    @Test
    void runtimeExceptionReturnsInternalServerError() {
        ResponseEntity<Map<String, String>> response =
                handler.handleRuntimeException(new RuntimeException("boom"));
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode());
        assertEquals("The request could not be processed", response.getBody().get("error"));
    }

    @Test
    void genericExceptionReturnsUnexpectedError() {
        ResponseEntity<Map<String, String>> response = handler.handleGenericException(new Exception("boom"));
        assertEquals(HttpStatus.INTERNAL_SERVER_ERROR, response.getStatusCode());
        assertEquals("An unexpected error occurred", response.getBody().get("error"));
    }
}