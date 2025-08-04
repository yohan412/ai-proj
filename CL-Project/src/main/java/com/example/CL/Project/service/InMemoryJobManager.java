package com.example.CL.Project.service;

import com.example.CL.Project.dto.AnalysisResult;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class InMemoryJobManager {

    private static final long JOB_EXPIRATION_MS = 3600000; // 1 hour

    private final Map<String, JobEntry> jobs = new ConcurrentHashMap<>();

    public void submitJob(String jobId, CompletableFuture<AnalysisResult> future) {
        jobs.put(jobId, new JobEntry(future));
    }

    public CompletableFuture<AnalysisResult> getJob(String jobId) {
        JobEntry entry = jobs.get(jobId);
        if (entry != null) {
            entry.updateLastAccessed();
            return entry.getFuture();
        }
        return null;
    }

    @Scheduled(fixedRate = 600000) // Run every 10 minutes
    public void cleanUpOldJobs() {
        System.out.println("Running scheduled job cleanup...");
        long now = Instant.now().toEpochMilli();
        jobs.entrySet().removeIf(entry -> {
            JobEntry jobEntry = entry.getValue();
            boolean isCompleted = jobEntry.getFuture().isDone();
            boolean isExpired = (now - jobEntry.getLastAccessed()) > JOB_EXPIRATION_MS;
            if (isCompleted && isExpired) {
                System.out.println("Removing expired job: " + entry.getKey());
                return true;
            }
            return false;
        });
    }

    private static class JobEntry {
        private final CompletableFuture<AnalysisResult> future;
        private long lastAccessed;

        JobEntry(CompletableFuture<AnalysisResult> future) {
            this.future = future;
            this.lastAccessed = Instant.now().toEpochMilli();
        }

        CompletableFuture<AnalysisResult> getFuture() {
            return future;
        }

        long getLastAccessed() {
            return lastAccessed;
        }

        void updateLastAccessed() {
            this.lastAccessed = Instant.now().toEpochMilli();
        }
    }
}
