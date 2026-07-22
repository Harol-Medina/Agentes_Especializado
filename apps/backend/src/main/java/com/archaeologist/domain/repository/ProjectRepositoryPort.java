package com.archaeologist.domain.repository;

import com.archaeologist.domain.model.Project;

import java.util.Optional;
import java.util.UUID;

public interface ProjectRepositoryPort {

    Project save(Project project);

    Optional<Project> findById(UUID id);

    Optional<Project> findByJobId(UUID jobId);
}
