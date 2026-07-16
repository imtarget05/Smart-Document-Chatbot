package com.smartdocchat.service;

import com.smartdocchat.entity.Evaluation;
import com.smartdocchat.repository.EvaluationRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class EvaluationService {
    private final EvaluationRepository repository;

    public List<Evaluation> getAllEvaluations() {
        return repository.findAll();
    }

    public Evaluation createEvaluation(Evaluation payload) {
        return repository.save(payload);
    }
}
