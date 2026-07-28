"use client";

import { useState, useCallback, useRef } from "react";
import { API_BASE_URL } from "@/lib/constants";

function generateId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export interface ChatSource {
  file: string;
  score?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  isStreaming?: boolean;
}

interface UseChatReturn {
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  sendMessage: (question: string) => void;
}

// ─────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────

export function useChat(projectId: string): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim() || isStreaming) return;

      setError(null);

      // Add user message
      const userMsg: ChatMessage = {
        id: generateId(),
        role: "user",
        content: question.trim(),
      };

      // Create placeholder assistant message
      const assistantMsg: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      // Abort any previous stream
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch(`${API_BASE_URL}/v1/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({ projectId, question: question.trim() }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          const msg =
            (body as { message?: string }).message ||
            `Request failed (${res.status})`;
          throw new Error(msg);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";
        let accumulatedContent = "";
        let sources: ChatSource[] | undefined;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE lines
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let eventType = "";

          for (const line of lines) {
            if (line.startsWith("event:")) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              const dataStr = line.slice(5).trim();

              try {
                const data = JSON.parse(dataStr);

                switch (eventType) {
                  case "context":
                  case "sources": {
                    const chunks =
                      data.chunks || data.files || [];
                    sources = Array.isArray(chunks)
                      ? chunks.map((c: string | { file: string; score?: number }) =>
                          typeof c === "string" ? { file: c } : c
                        )
                      : [];
                    break;
                  }
                  case "token": {
                    accumulatedContent += data.content || "";
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantMsg.id
                          ? { ...m, content: accumulatedContent, sources }
                          : m
                      )
                    );
                    break;
                  }
                  case "done": {
                    // Finalize the message
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantMsg.id
                          ? {
                              ...m,
                              content: accumulatedContent,
                              sources,
                              isStreaming: false,
                            }
                          : m
                      )
                    );
                    break;
                  }
                  case "no_context": {
                    accumulatedContent =
                      data.message ||
                      "No relevant information found for this question.";
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantMsg.id
                          ? {
                              ...m,
                              content: accumulatedContent,
                              isStreaming: false,
                            }
                          : m
                      )
                    );
                    break;
                  }
                  case "error": {
                    const errMsg =
                      data.message || data.error || "An error occurred";
                    setError(errMsg);
                    setMessages((prev) =>
                      prev.map((m) =>
                        m.id === assistantMsg.id
                          ? {
                              ...m,
                              content: `Error: ${errMsg}`,
                              isStreaming: false,
                            }
                          : m
                      )
                    );
                    break;
                  }
                  case "heartbeat":
                    // Ignore keepalive
                    break;
                }
              } catch {
                // Ignore malformed JSON lines
              }
            } else if (line === "") {
              // Reset event type on blank line (end of SSE block)
              eventType = "";
            }
          }
        }

        // Ensure streaming flag is cleared even if no "done" event received
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? { ...m, isStreaming: false }
              : m
          )
        );
      } catch (err: unknown) {
        if ((err as Error).name === "AbortError") return;

        const message =
          err instanceof Error ? err.message : "Failed to send message";
        setError(message);

        // Remove the empty assistant message on error
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? { ...m, content: `Error: ${message}`, isStreaming: false }
              : m
          )
        );
      } finally {
        setIsStreaming(false);
      }
    },
    [projectId, isStreaming]
  );

  return { messages, isStreaming, error, sendMessage };
}
