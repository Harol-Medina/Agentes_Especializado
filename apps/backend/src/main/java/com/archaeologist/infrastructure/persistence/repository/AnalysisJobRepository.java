package com.archaeologist.infrastructure.persistence.repository;

import com.archaeologist.infrastructure.persistence.entity.AnalysisJobEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface AnalysisJobRepository extends JpaRepository<AnalysisJobEntity, UUID> {
}
