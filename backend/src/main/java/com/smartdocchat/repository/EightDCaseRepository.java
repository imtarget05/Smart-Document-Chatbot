package com.smartdocchat.repository;

import com.smartdocchat.entity.EightDCase;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface EightDCaseRepository extends JpaRepository<EightDCase, Long> {
}
