package com.smartdocchat.repository;

import com.smartdocchat.entity.DataSource;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DataSourceRepository extends JpaRepository<DataSource, Long> {
    Optional<DataSource> findByName(String name);
    List<DataSource> findByType(DataSource.SourceType type);
    List<DataSource> findByStatus(DataSource.SyncStatus status);
    boolean existsByName(String name);
}
