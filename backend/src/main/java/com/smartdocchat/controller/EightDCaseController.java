package com.smartdocchat.controller;

import com.smartdocchat.entity.EightDCase;
import com.smartdocchat.service.EightDCaseService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/8d-cases")
@RequiredArgsConstructor
@PreAuthorize("hasAnyRole('ENGINEER','ADMIN')")
public class EightDCaseController {
    private final EightDCaseService eightDCaseService;

    @GetMapping
    public ResponseEntity<List<EightDCase>> getAllCases() {
        return ResponseEntity.ok(eightDCaseService.getAllCases());
    }

    @GetMapping("/{id}")
    public ResponseEntity<EightDCase> getCaseById(@PathVariable Long id) {
        return eightDCaseService.getCaseById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<EightDCase> createCase(@RequestBody EightDCase payload) {
        return ResponseEntity.ok(eightDCaseService.createCase(payload));
    }

    @PutMapping("/{id}")
    public ResponseEntity<EightDCase> updateCase(@PathVariable Long id, @RequestBody EightDCase payload) {
        return eightDCaseService.updateCase(id, payload)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PatchMapping("/{id}/step/{step}")
    public ResponseEntity<EightDCase> updateStep(
            @PathVariable Long id,
            @PathVariable String step,
            @RequestBody Map<String, String> body) {
        String content = body.getOrDefault("content", "");
        return eightDCaseService.updateStep(id, step.toUpperCase(), content)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PatchMapping("/{id}/status")
    public ResponseEntity<EightDCase> updateStatus(
            @PathVariable Long id,
            @RequestBody Map<String, String> body) {
        String status = body.getOrDefault("status", "IN_PROGRESS");
        return eightDCaseService.updateStatus(id, status)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> deleteCase(@PathVariable Long id) {
        if (eightDCaseService.deleteCase(id)) {
            return ResponseEntity.noContent().build();
        }
        return ResponseEntity.notFound().build();
    }
}