package com.archaeologist.domain.repository;

import com.archaeologist.domain.model.AgentResult;

import java.util.List;
import java.util.UUID;

public interface AgentResultRepositoryPort {

    AgentResult save(AgentResult agentResult);

    List<AgentResult> findByJobId(UUID jobId);
}
