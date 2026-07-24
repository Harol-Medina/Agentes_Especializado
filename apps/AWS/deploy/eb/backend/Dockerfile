# =============================================================================
# Software Archaeologist — EB-Compatible Backend Dockerfile
#
# This Dockerfile is designed for Elastic Beanstalk's Docker platform.
# Unlike the project's root Dockerfile (docker/backend/Dockerfile) which
# expects the full repo context (COPY apps/backend/ .), this one works as
# a standalone build — the source bundle contains this Dockerfile alongside
# the backend source code at the same level.
#
# Build context expected:
#   source-bundle/
#   ├── Dockerfile       (this file)
#   └── backend/         (copy of apps/backend/)
#
# The deploy script (03-deploy-backend-eb.sh) assembles this layout before
# creating the source bundle zip.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build — Compile the Spring Boot application
#
# Uses the official Gradle image with JDK 21. The --no-daemon flag prevents
# Gradle from spawning a long-lived process inside the container (wasteful
# in CI/build contexts where the container is ephemeral).
# ---------------------------------------------------------------------------
FROM gradle:8-jdk21 AS build

WORKDIR /app

# Copy the backend source into the build container
COPY backend/ .

# Build the fat JAR (bootJar) without running tests — tests should pass
# in CI before reaching the deploy phase.
RUN gradle bootJar --no-daemon -x test

# ---------------------------------------------------------------------------
# Stage 2: Runtime — Minimal JRE image
#
# Alpine-based for small footprint (~200MB vs ~400MB full JRE).
# Non-root user for security (Requirement 14 — minimal privilege).
# ---------------------------------------------------------------------------
FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

# Create a non-root user to run the application (security best practice)
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy the compiled JAR from the build stage
COPY --from=build /app/build/libs/*.jar app.jar

# Change ownership to non-root user
RUN chown appuser:appgroup app.jar

USER appuser

# EB Docker platform routes traffic to this port.
# Must match the SERVER_PORT environment variable configured in EB.
EXPOSE 8080

# Spring Boot actuator health endpoint is available at /actuator/health
# EB will use this for health checks.
ENTRYPOINT ["java", "-jar", "app.jar"]
