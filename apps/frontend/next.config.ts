import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Build output compatible with the Docker multi-stage build in docker/frontend/Dockerfile
  // which copies .next + node_modules directly from the build stage
};

export default nextConfig;
