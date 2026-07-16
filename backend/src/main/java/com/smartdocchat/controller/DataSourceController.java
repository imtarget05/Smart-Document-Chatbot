package com.smartdocchat.controller;

import com.smartdocchat.entity.DataSource;
import com.smartdocchat.service.DataSourceService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/datasources")
@RequiredArgsConstructor
@PreAuthorize("hasAnyRole('ENGINEER','ADMIN')")
public class DataSourceController {
    private final DataSourceService dataSourceService;

    @GetMapping
    public ResponseEntity<List<DataSource>> getAllDataSources() {
        return ResponseEntity.ok(dataSourceService.getAllDataSources());
    }

    @GetMapping("/{id}")
    public ResponseEntity<DataSource> getDataSourceById(@PathVariable Long id) {
        return dataSourceService.getDataSourceById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<DataSource> createDataSource(@Valid @RequestBody DataSource dataSource) {
        return ResponseEntity.ok(dataSourceService.createDataSource(dataSource));
    }

    @PutMapping("/{id}")
    public ResponseEntity<DataSource> updateDataSource(@PathVariable Long id, @Valid @RequestBody DataSource dataSource) {
        return dataSourceService.updateDataSource(id, dataSource)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteDataSource(@PathVariable Long id) {
        return dataSourceService.deleteDataSource(id)
                ? ResponseEntity.noContent().build()
                : ResponseEntity.notFound().build();
    }
}
