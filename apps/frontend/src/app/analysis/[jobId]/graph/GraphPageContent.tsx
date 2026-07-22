"use client";

import { DependencyGraph } from "@/components/graph/DependencyGraph";

interface GraphPageContentProps {
  jobId: string;
}

export function GraphPageContent({ jobId }: GraphPageContentProps) {
  // The jobId acts as the projectId for the graph endpoint
  // In the real flow, after analysis completes, the jobId maps to a projectId
  return (
    <div className="h-full w-full">
      <DependencyGraph projectId={jobId} />
    </div>
  );
}
