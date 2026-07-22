import { Header } from "@/components/shared/Header";
import { GraphPageContent } from "./GraphPageContent";

interface GraphPageProps {
  params: Promise<{ jobId: string }>;
}

export default async function GraphPage({ params }: GraphPageProps) {
  const { jobId } = await params;

  return (
    <>
      <Header />
      <main className="h-[calc(100vh-60px)] overflow-hidden">
        <GraphPageContent jobId={jobId} />
      </main>
    </>
  );
}
