package com.smartdocchat.controller;

import com.smartdocchat.entity.Evaluation;
import com.smartdocchat.service.EvaluationService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/evaluations")
@RequiredArgsConstructor
@PreAuthorize("hasAnyRole('ENGINEER','ADMIN')")
public class EvaluationController {
    private final EvaluationService evaluationService;

    @GetMapping
    public ResponseEntity<List<Evaluation>> getAllEvaluations() {
        return ResponseEntity.ok(evaluationService.getAllEvaluations());
    }

    @PostMapping
    public ResponseEntity<Evaluation> createEvaluation(@RequestBody Evaluation payload) {
        return ResponseEntity.ok(evaluationService.createEvaluation(payload));
    }
}
