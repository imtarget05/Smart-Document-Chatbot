package com.smartdocchat.repository;

import com.smartdocchat.entity.Document;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DocumentRepository extends JpaRepository<Document, Long> {
    List<Document> findByOrderByCreatedAtDesc();
    Document findByFilePath(String filePath);
}
