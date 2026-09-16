package com.smartdocchat.repository;

import com.smartdocchat.entity.LegalChunk;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Repository
public interface LegalChunkRepository extends JpaRepository<LegalChunk, Long> {
    List<LegalChunk> findByDocumentIdOrderByOrdinalAsc(Long documentId);

    @Modifying
    @Transactional
    @Query("DELETE FROM LegalChunk lc WHERE lc.documentId = :documentId")
    void deleteByDocumentId(@Param("documentId") Long documentId);
}