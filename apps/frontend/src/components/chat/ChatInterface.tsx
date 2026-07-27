"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { useChat } from "@/hooks/useChat";
import { ChatMessage } from "./ChatMessage";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

interface ChatInterfaceProps {
  projectId: string;
}

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

export function ChatInterface({ projectId }: ChatInterfaceProps) {
  const { messages, isStreaming, error, sendMessage } = useChat(projectId);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    sendMessage(input);
    setInput("");
  }

  return (
    <div className="flex flex-col h-[calc(100vh-60px)]">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="container max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && (
            <EmptyState />
          )}

          {messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              role={msg.role}
              content={msg.content}
              sources={msg.sources}
            />
          ))}

          {/* Typing indicator */}
          {isStreaming && messages[messages.length - 1]?.content === "" && (
            <TypingIndicator />
          )}

          <div ref={messagesEndRef} aria-hidden="true" />
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-4 py-2 bg-[#EF4444]/10 border-t border-[#EF4444]/30 text-center">
          <p className="font-code text-xs text-[#EF4444]">{error}</p>
        </div>
      )}

      {/* Input area */}
      <div className="border-t border-border bg-card/50 backdrop-blur-sm px-4 py-4">
        <form
          onSubmit={handleSubmit}
          className="container max-w-3xl mx-auto flex items-center gap-3"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about the codebase..."
            disabled={isStreaming}
            className={cn(
              "flex-1 h-10 px-4",
              "bg-muted border border-border rounded-md",
              "font-sans text-sm text-foreground placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-colors duration-150"
            )}
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            aria-label="Send message"
            className={cn(
              "h-10 px-4 rounded-md",
              "bg-primary text-primary-foreground",
              "font-sans text-sm font-semibold",
              "hover:bg-primary/90",
              "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-all duration-150"
            )}
          >
            {isStreaming ? (
              <LoadingSpinner />
            ) : (
              <SendIcon />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/30 flex items-center justify-center mb-4">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          className="text-primary"
        >
          <path
            d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <h2 className="font-heading text-lg font-bold text-foreground mb-2">
        Ask about this codebase
      </h2>
      <p className="font-sans text-sm text-muted-foreground max-w-sm">
        Ask questions about architecture, dependencies, patterns, or any aspect
        of the analyzed repository. Responses are powered by RAG over the source code.
      </p>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="bg-card border border-border rounded-xl px-4 py-3 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:0ms]" />
        <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:150ms]" />
        <span className="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-bounce [animation-delay:300ms]" />
      </div>
    </div>
  );
}

function SendIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M22 2L11 13"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M22 2L15 22L11 13L2 9L22 2Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function LoadingSpinner() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      className="animate-spin"
      aria-hidden="true"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="2"
        strokeDasharray="60"
        strokeDashoffset="20"
        strokeLinecap="round"
      />
    </svg>
  );
}
