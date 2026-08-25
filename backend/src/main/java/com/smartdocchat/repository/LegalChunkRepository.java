package com.smartdocchat.repository;

import com.smartdocchat.entity.LegalChunk;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface LegalChunkRepository extends JpaRepository<LegalChunk, Long> {
    List<LegalChunk> findByDocumentIdOrderByOrdinalAsc(Long documentId);
    long deleteByDocumentId(Long documentId);
}