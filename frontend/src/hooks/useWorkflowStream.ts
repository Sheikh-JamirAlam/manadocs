import { useEffect } from "react";

export type WorkflowEvent = {
  id: number;
  document_id: string;
  thread_id: string;
  node_name?: string | null;
  event_type: string;
  message?: string | null;
  details?: { status?: string; error_message?: string | null };
  created_at: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function useWorkflowStream(threadId: string | undefined, onEvent: (event: WorkflowEvent) => void) {
  useEffect(() => {
    if (!threadId) return;
    const source = new EventSource(`${apiBaseUrl}/workflow/${encodeURIComponent(threadId)}/events/stream`);
    const handleEvent = (message: MessageEvent<string>) => {
      try {
        onEvent(JSON.parse(message.data) as WorkflowEvent);
      } catch {
        // Ignore malformed events so one bad message does not break the stream.
      }
    };
    source.addEventListener("workflow", handleEvent);
    return () => {
      source.removeEventListener("workflow", handleEvent);
      source.close();
    };
  }, [threadId, onEvent]);
}
