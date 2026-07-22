/** Base URL for backend API calls — injected via NEXT_PUBLIC_API_URL env var */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "/api";

/** Polling interval for analysis job status (ms) */
export const POLLING_INTERVAL_MS = 5_000;

/** GitHub URL pattern for client-side validation */
export const GITHUB_URL_PATTERN =
  /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/;

/** Agent pipeline stage names in execution order */
export const AGENT_STAGES = [
  "repository_agent",
  "architecture_agent",
  "quality_agent",
  "security_agent",
  "documentation_agent",
  "modernization_agent",
  "kiro_agent",
] as const;

export type AgentStage = (typeof AGENT_STAGES)[number];

/** Human-readable labels for each agent stage */
export const AGENT_LABELS: Record<AgentStage, string> = {
  repository_agent: "Repository",
  architecture_agent: "Architecture",
  quality_agent: "Quality",
  security_agent: "Security",
  documentation_agent: "Documentation",
  modernization_agent: "Modernization",
  kiro_agent: "Kiro Spec",
};
