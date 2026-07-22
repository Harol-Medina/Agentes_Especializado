package com.archaeologist.infrastructure.persistence.repository;

import com.archaeologist.infrastructure.persistence.entity.AgentResultEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface AgentResultRepository extends JpaRepository<AgentResultEntity, UUID> {

    List<AgentResultEntity> findByJobIdOrderByExecutionOrder(UUID jobId);
}
