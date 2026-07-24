package com.archaeologist.infrastructure.scheduling;

import com.archaeologist.domain.model.AnalysisJob;
import com.archaeologist.domain.model.JobStatus;
import com.archaeologist.domain.service.JobQueueService;
import com.archaeologist.infrastructure.web.controller.AnalysisJobController;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.UUID;

/**
 * Periodic cleanup that detects stale jobs (stuck in non-terminal state
 * beyond the configured timeout) and releases the processing slot.
 *
 * This prevents permanent slot lockout if the Analyzer crashes without
 * sending the completion webhook.
 */
@Component
public class StaleJobCleanupTask {

    private static final Logger log = LoggerFactory.getLogger(StaleJobCleanupTask.class);

    private final JobQueueService jobQueueService;
    private final AnalysisJobController analysisJobController;
    private final int timeoutMinutes;

    public StaleJobCleanupTask(
            JobQueueService jobQueueService,
            AnalysisJobController analysisJobController,
            @Value("${app.job-timeout-minutes:30}") int timeoutMinutes) {
        this.jobQueueService = jobQueueService;
        this.analysisJobController = analysisJobController;
        this.timeoutMinutes = timeoutMinutes;
    }

    @Scheduled(fixedDelayString = "${app.stale-job-check-interval-ms:60000}")
    public void releaseStaleJobs() {
        jobQueueService.getActiveJobId().ifPresent(activeJobId -> {
            Map<UUID, AnalysisJob> jobStore = analysisJobController.getJobStore();
            AnalysisJob job = jobStore.get(activeJobId);

            if (job == null) {
                // Job exists in queue but not in store — orphaned slot, release it
                log.warn("Orphaned slot detected for job_id={}, releasing", activeJobId);
                jobQueueService.release(activeJobId);
                return;
            }

            // Only clean up non-terminal jobs that have exceeded the timeout
            if (job.status() != JobStatus.COMPLETED && job.status() != JobStatus.FAILED) {
                LocalDateTime cutoff = LocalDateTime.now().minusMinutes(timeoutMinutes);
                if (job.updatedAt().isBefore(cutoff)) {
                    log.warn(
                        "Stale job detected — job_id={}, status={}, updatedAt={}, timeout={}min. Marking failed and releasing slot.",
                        activeJobId, job.status(), job.updatedAt(), timeoutMinutes
                    );

                    AnalysisJob failedJob = new AnalysisJob(
                        job.id(),
                        job.repoUrl(),
                        JobStatus.FAILED,
                        null,
                        job.createdAt(),
                        LocalDateTime.now(),
                        null,
                        "Analysis timed out after " + timeoutMinutes + " minutes without completion"
                    );
                    jobStore.put(activeJobId, failedJob);
                    jobQueueService.release(activeJobId);
                }
            }
        });
    }
}
