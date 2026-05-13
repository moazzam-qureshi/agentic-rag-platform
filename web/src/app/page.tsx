import { AppShell } from "@/components/AppShell";
import { ChatPanel } from "@/components/ChatPanel";
import { RetrievalTrace } from "@/components/RetrievalTrace";
import { Sidebar } from "@/components/Sidebar";
import { ChatProvider } from "@/hooks/useChat";

export default function HomePage() {
  return (
    <ChatProvider>
      <AppShell
        sidebar={<Sidebar />}
        main={<ChatPanel />}
        rightRail={<RetrievalTrace />}
      />
    </ChatProvider>
  );
}
