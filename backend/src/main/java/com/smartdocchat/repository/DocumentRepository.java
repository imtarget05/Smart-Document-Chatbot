package com.smartdocchat.repository;

import com.smartdocchat.entity.Document;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DocumentRepository extends JpaRepository<Document, Long> {
    List<Document> findByOrderByCreatedAtDesc();
    List<Document> findByOwnerUsernameOrderByCreatedAtDesc(String ownerUsername);
    Optional<Document> findByIdAndOwnerUsername(Long id, String ownerUsername);
    Document findByFilePath(String filePath);
}
