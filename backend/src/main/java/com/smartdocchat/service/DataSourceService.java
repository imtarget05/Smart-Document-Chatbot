package com.smartdocchat.service;

import com.smartdocchat.entity.DataSource;
import com.smartdocchat.repository.DataSourceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class DataSourceService {
    private final DataSourceRepository dataSourceRepository;

    public List<DataSource> getAllDataSources() {
        return dataSourceRepository.findAll();
    }

    public Optional<DataSource> getDataSourceById(Long id) {
        return dataSourceRepository.findById(id);
    }

    public DataSource createDataSource(DataSource dataSource) {
        return dataSourceRepository.save(dataSource);
    }

    public Optional<DataSource> updateDataSource(Long id, DataSource payload) {
        return dataSourceRepository.findById(id).map(existing -> {
            existing.setName(payload.getName());
            existing.setType(payload.getType());
            existing.setConnectionUrl(payload.getConnectionUrl());
            existing.setDescription(payload.getDescription());
            existing.setStatus(payload.getStatus());
            return dataSourceRepository.save(existing);
        });
    }

    public boolean deleteDataSource(Long id) {
        if (!dataSourceRepository.existsById(id)) {
            return false;
        }
        dataSourceRepository.deleteById(id);
        return true;
    }
}
