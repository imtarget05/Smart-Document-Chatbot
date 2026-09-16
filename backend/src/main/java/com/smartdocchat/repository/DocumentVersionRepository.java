package com.smartdocchat.repository;

import com.smartdocchat.entity.DocumentVersion;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Repository
public interface DocumentVersionRepository extends JpaRepository<DocumentVersion, Long> {

    List<DocumentVersion> findByDocumentIdOrderByVersionNumberDesc(Long documentId);

    Optional<DocumentVersion> findByDocumentIdAndVersionNumber(Long documentId, Integer versionNumber);

    Optional<DocumentVersion> findTopByDocumentIdOrderByVersionNumberDesc(Long documentId);

    Long countByDocumentId(Long documentId);

    @Query("SELECT v.documentId, COUNT(v) FROM DocumentVersion v GROUP BY v.documentId")
    List<Object[]> countAllGroupedByDocumentId();

    @Modifying
    @Transactional
    @Query("DELETE FROM DocumentVersion v WHERE v.documentId = :documentId")
    void deleteByDocumentId(@Param("documentId") Long documentId);
}
