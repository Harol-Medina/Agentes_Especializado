import { Header } from "@/components/shared/Header";
import { ArchitectureReport } from "@/components/report/ArchitectureReport";

interface ReportPageProps {
  params: Promise<{ jobId: string }>;
}

export default async function ReportPage({ params }: ReportPageProps) {
  const { jobId } = await params;

  return (
    <>
      <Header />
      <main className="relative min-h-[calc(100vh-60px)] overflow-hidden">
        {/* Background effects */}
        <div
          className="absolute inset-0 bg-grid pointer-events-none"
          aria-hidden="true"
        />
        <div
          className="absolute inset-0 hero-glow pointer-events-none"
          aria-hidden="true"
        />

        {/* Report content */}
        <div className="relative z-10">
          <ArchitectureReport projectId={jobId} />
        </div>
      </main>
    </>
  );
}
