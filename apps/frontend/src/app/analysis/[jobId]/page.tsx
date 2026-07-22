import { Header } from "@/components/shared/Header";
import { AnalysisProgress } from "@/components/shared/AnalysisProgress";

interface AnalysisPageProps {
  params: Promise<{ jobId: string }>;
}

export default async function AnalysisPage({ params }: AnalysisPageProps) {
  const { jobId } = await params;

  return (
    <>
      <Header />
      <main className="relative min-h-[calc(100vh-60px)] overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 bg-grid pointer-events-none" aria-hidden="true" />
        <div className="absolute inset-0 hero-glow pointer-events-none" aria-hidden="true" />

        <AnalysisProgress jobId={jobId} />
      </main>
    </>
  );
}
