import { API_BASE_URL } from "./constants";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export type JobStatus =
  | "pending"
  | "cloning"
  | "analyzing"
  | "completed"
  | "failed";

export type AgentStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped";

export interface AgentProgress {
  name: string;
  status: AgentStatus;
}

export interface AnalysisJobResponse {
  jobId: string;
  status: JobStatus;
  currentAgent: string | null;
  progress: {
    totalAgents: number;
    completedAgents: number;
    agents: AgentProgress[];
  };
  createdAt: string;
}

export interface SubmitJobRequest {
  repoUrl: string;
}

export interface SubmitJobResponse {
  jobId: string;
  status: JobStatus;
  message: string;
}

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

// ─────────────────────────────────────────────
// API client
// ─────────────────────────────────────────────

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw { status: res.status, ...(body as ApiError) };
  }
  return res.json() as Promise<T>;
}

export async function submitJob(
  repoUrl: string
): Promise<SubmitJobResponse> {
  const res = await fetch(`${API_BASE_URL}/v1/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repoUrl } satisfies SubmitJobRequest),
  });
  return handleResponse<SubmitJobResponse>(res);
}

export async function getJobStatus(
  jobId: string
): Promise<AnalysisJobResponse> {
  const res = await fetch(`${API_BASE_URL}/v1/jobs/${jobId}`);
  return handleResponse<AnalysisJobResponse>(res);
}
