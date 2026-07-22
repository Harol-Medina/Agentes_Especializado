import { Header } from "@/components/shared/Header";
import { ChatInterface } from "@/components/chat/ChatInterface";

interface ChatPageProps {
  params: Promise<{ jobId: string }>;
}

export default async function ChatPage({ params }: ChatPageProps) {
  const { jobId } = await params;

  // In the full app, jobId maps to a projectId via the Backend.
  // For MVP, we use jobId as the projectId identifier.
  const projectId = jobId;

  return (
    <>
      <Header />
      <ChatInterface projectId={projectId} />
    </>
  );
}
