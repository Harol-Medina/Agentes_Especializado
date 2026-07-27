package com.archaeologist.infrastructure.web.controller;

import com.archaeologist.domain.model.AnalysisJob;
import com.archaeologist.domain.model.JobStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.*;
import java.util.stream.Collectors;

/**
 * Dashboard summary endpoint — provides aggregated metrics and recent jobs
 * for the frontend dashboard to consume.
 *
 * <p>Reads from the in-memory job store (same as AnalysisJobController).
 * In production, this would query the database for persistent data.
 */
@RestController
@RequestMapping("/api/v1/dashboard")
public class DashboardController {

    private final AnalysisJobController analysisJobController;

    public DashboardController(AnalysisJobController analysisJobController) {
        this.analysisJobController = analysisJobController;
    }

    /**
     * GET /api/v1/dashboard — returns aggregated dashboard data.
     */
    @GetMapping
    public ResponseEntity<Map<String, Object>> getDashboard() {
        Map<UUID, AnalysisJob> jobStore = analysisJobController.getJobStore();
        Collection<AnalysisJob> allJobs = jobStore.values();

        // Metrics
        long totalProjects = allJobs.size();
        long completedProjects = allJobs.stream()
            .filter(j -> j.status() == JobStatus.COMPLETED)
            .count();
        long analyzingProjects = allJobs.stream()
            .filter(j -> j.status() == JobStatus.ANALYZING || j.status() == JobStatus.CLONING)
            .count();
        long failedProjects = allJobs.stream()
            .filter(j -> j.status() == JobStatus.FAILED)
            .count();
        long queuedProjects = allJobs.stream()
            .filter(j -> j.status() == JobStatus.PENDING)
            .count();

        double successRate = totalProjects > 0
            ? Math.round((completedProjects * 1000.0) / totalProjects) / 10.0
            : 0.0;

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("totalProjects", totalProjects);
        metrics.put("completedProjects", completedProjects);
        metrics.put("analyzingProjects", analyzingProjects);
        metrics.put("failedProjects", failedProjects);
        metrics.put("queuedProjects", queuedProjects);
        metrics.put("successRate", successRate);
        metrics.put("activeAgents", analyzingProjects > 0 ? 7 : 0);
        metrics.put("totalAgents", 7);

        // Recent jobs (last 10, sorted by creation date desc)
        List<Map<String, Object>> recentJobs = allJobs.stream()
            .sorted(Comparator.comparing(AnalysisJob::createdAt, Comparator.nullsLast(Comparator.reverseOrder())))
            .limit(10)
            .map(this::jobToMap)
            .collect(Collectors.toList());

        // Build response
        Map<String, Object> dashboard = new LinkedHashMap<>();
        dashboard.put("metrics", metrics);
        dashboard.put("recentJobs", recentJobs);
        dashboard.put("systemStatus", analyzingProjects > 0 ? "active" : "idle");

        return ResponseEntity.ok(dashboard);
    }

    private Map<String, Object> jobToMap(AnalysisJob job) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("id", job.id().toString());
        map.put("repoUrl", job.repoUrl());
        map.put("name", extractRepoName(job.repoUrl()));
        map.put("status", job.status().name().toLowerCase());
        map.put("currentAgent", job.currentAgent());
        map.put("createdAt", job.createdAt() != null ? job.createdAt().toString() : null);
        return map;
    }

    private String extractRepoName(String repoUrl) {
        if (repoUrl == null || repoUrl.isBlank()) return "unknown";
        String trimmed = repoUrl.endsWith("/") ? repoUrl.substring(0, repoUrl.length() - 1) : repoUrl;
        int lastSlash = trimmed.lastIndexOf('/');
        return lastSlash >= 0 ? trimmed.substring(lastSlash + 1) : trimmed;
    }
}
