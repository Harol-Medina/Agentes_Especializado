import { Header } from "@/components/shared/Header";
import { KiroExport } from "@/components/report/KiroExport";

interface ExportPageProps {
  params: Promise<{ jobId: string }>;
}

export default async function ExportPage({ params }: ExportPageProps) {
  const { jobId } = await params;

  return (
    <>
      <Header />
      <main className="relative min-h-[calc(100vh-60px)] overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 bg-grid pointer-events-none" aria-hidden="true" />
        <div className="absolute inset-0 hero-glow pointer-events-none" aria-hidden="true" />

        <div className="relative z-10">
          <KiroExport projectId={jobId} />
        </div>
      </main>
    </>
  );
}
