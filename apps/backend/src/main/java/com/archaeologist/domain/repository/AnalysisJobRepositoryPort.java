package com.archaeologist.domain.repository;

import com.archaeologist.domain.model.AnalysisJob;

import java.util.Optional;
import java.util.UUID;

public interface AnalysisJobRepositoryPort {

    AnalysisJob save(AnalysisJob job);

    Optional<AnalysisJob> findById(UUID id);
}
