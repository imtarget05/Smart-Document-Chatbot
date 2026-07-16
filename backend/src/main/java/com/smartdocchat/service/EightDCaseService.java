package com.smartdocchat.service;

import com.smartdocchat.entity.EightDCase;
import com.smartdocchat.repository.EightDCaseRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class EightDCaseService {
    private final EightDCaseRepository repository;

    public List<EightDCase> getAllCases() {
        return repository.findAll();
    }

    public Optional<EightDCase> getCaseById(Long id) {
        return repository.findById(id);
    }

    public EightDCase createCase(EightDCase payload) {
        return repository.save(payload);
    }

    public Optional<EightDCase> updateCase(Long id, EightDCase payload) {
        return repository.findById(id).map(existing -> {
            existing.setTitle(payload.getTitle());
            existing.setSeverity(payload.getSeverity());
            existing.setStatus(payload.getStatus());
            existing.setOwner(payload.getOwner());
            existing.setSummary(payload.getSummary());
            existing.setD1Team(payload.getD1Team());
            existing.setD2Describe(payload.getD2Describe());
            existing.setD3Containment(payload.getD3Containment());
            existing.setD4RootCause(payload.getD4RootCause());
            existing.setD5Corrective(payload.getD5Corrective());
            existing.setD6Verification(payload.getD6Verification());
            existing.setD7Preventive(payload.getD7Preventive());
            existing.setD8Recognition(payload.getD8Recognition());
            existing.setTimeline(payload.getTimeline());
            existing.setAiSuggestions(payload.getAiSuggestions());
            existing.setDocumentId(payload.getDocumentId());
            return repository.save(existing);
        });
    }

    public Optional<EightDCase> updateStep(Long id, String step, String content) {
        return repository.findById(id).map(existing -> {
            switch (step) {
                case "D1": existing.setD1Team(content); break;
                case "D2": existing.setD2Describe(content); break;
                case "D3": existing.setD3Containment(content); break;
                case "D4": existing.setD4RootCause(content); break;
                case "D5": existing.setD5Corrective(content); break;
                case "D6": existing.setD6Verification(content); break;
                case "D7": existing.setD7Preventive(content); break;
                case "D8": existing.setD8Recognition(content); break;
                default: throw new IllegalArgumentException("Invalid 8D step: " + step);
            }
            return repository.save(existing);
        });
    }

    public Optional<EightDCase> updateStatus(Long id, String status) {
        return repository.findById(id).map(existing -> {
            existing.setStatus(status);
            if ("CLOSED".equals(status)) {
                existing.setD8Recognition("Case closed at " + LocalDateTime.now());
            }
            return repository.save(existing);
        });
    }

    public boolean deleteCase(Long id) {
        if (repository.existsById(id)) {
            repository.deleteById(id);
            return true;
        }
        return false;
    }
}