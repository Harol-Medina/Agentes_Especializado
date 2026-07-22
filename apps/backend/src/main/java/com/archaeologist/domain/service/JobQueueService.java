package com.archaeologist.domain.service;

import org.springframework.stereotype.Service;

import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Single-slot sequential queue enforcement.
 * Only one analysis job can be active at a time.
 *
 * Limitation (MVP): Uses in-memory AtomicReference — works only with a single
 * Backend instance. For multi-instance production, migrate to PostgreSQL advisory
 * locks or SELECT FOR UPDATE SKIP LOCKED.
 */
@Service
public class JobQueueService {

    private final AtomicReference<UUID> activeJobId = new AtomicReference<>(null);

    /**
     * Attempts to acquire the processing slot for a new job.
     *
     * @param jobId the job ID requesting the slot
     * @return true if the slot was acquired, false if the system is busy
     */
    public boolean tryAcquire(UUID jobId) {
        return activeJobId.compareAndSet(null, jobId);
    }

    /**
     * Releases the processing slot. Only releases if the given jobId
     * matches the currently active job.
     *
     * @param jobId the job ID to release
     */
    public void release(UUID jobId) {
        activeJobId.compareAndSet(jobId, null);
    }

    /**
     * Checks if the system is currently processing a job.
     *
     * @return true if a job is currently active
     */
    public boolean isBusy() {
        return activeJobId.get() != null;
    }

    /**
     * Returns the ID of the currently active job, if any.
     *
     * @return Optional containing the active job ID, or empty if idle
     */
    public Optional<UUID> getActiveJobId() {
        return Optional.ofNullable(activeJobId.get());
    }
}
