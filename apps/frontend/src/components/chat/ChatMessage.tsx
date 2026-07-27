"use client";

import { cn } from "@/lib/utils";
import type { ChatSource } from "@/hooks/useChat";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
}

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────

export function ChatMessage({ role, content, sources }: ChatMessageProps) {
  const isUser = role === "user";

  return (
    <div
      className={cn(
        "flex w-full animate-fade-in",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[80%] rounded-xl px-4 py-3",
          isUser
            ? "bg-primary/10 border border-primary/30 text-foreground"
            : "bg-card border border-border text-card-foreground"
        )}
      >
        {/* Message content */}
        <div
          className={cn(
            "text-sm leading-relaxed whitespace-pre-wrap break-words",
            !isUser && "font-sans"
          )}
        >
          {renderContent(content)}
        </div>

        {/* Source file tags */}
        {sources && sources.length > 0 && (
          <div className="mt-3 pt-2 border-t border-border flex flex-wrap gap-1.5">
            {sources.map((source) => (
              <span
                key={source.file}
                className={cn(
                  "inline-flex items-center gap-1",
                  "font-code text-[10px] text-secondary",
                  "bg-secondary/10 border border-secondary/30",
                  "rounded-[3px] px-1.5 py-0.5"
                )}
                title={source.file}
              >
                <FileIcon />
                {truncateFilePath(source.file)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function FileIcon() {
  return (
    <svg
      width="10"
      height="10"
      viewBox="0 0 16 16"
      fill="none"
      className="shrink-0"
      aria-hidden="true"
    >
      <path
        d="M3 1.5h6.5L13 5v9.5a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-13a1 1 0 0 1 1-1h-.5z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path d="M9.5 1.5V5H13" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
    </svg>
  );
}

function truncateFilePath(path: string, maxLen = 40): string {
  if (path.length <= maxLen) return path;
  const parts = path.split("/");
  if (parts.length <= 2) return path;
  return `…/${parts.slice(-2).join("/")}`;
}

/**
 * Render content with inline code blocks styled properly.
 * Splits on backtick-fenced code blocks and inline code.
 */
function renderContent(content: string) {
  // Split on code blocks (```...```)
  const parts = content.split(/(```[\s\S]*?```)/g);

  return parts.map((part, i) => {
    if (part.startsWith("```") && part.endsWith("```")) {
      const codeContent = part.slice(3, -3).replace(/^\w*\n/, "");
      return (
        <pre
          key={i}
          className="my-2 p-3 bg-muted border border-border rounded-md overflow-x-auto"
        >
          <code className="font-code text-xs text-foreground">{codeContent}</code>
        </pre>
      );
    }

    // Handle inline code within regular text
    const inlineParts = part.split(/(`[^`]+`)/g);
    return (
      <span key={i}>
        {inlineParts.map((inline, j) => {
          if (inline.startsWith("`") && inline.endsWith("`")) {
            return (
              <code
                key={j}
                className="font-code text-xs bg-muted border border-border rounded px-1 py-0.5"
              >
                {inline.slice(1, -1)}
              </code>
            );
          }
          return <span key={j}>{inline}</span>;
        })}
      </span>
    );
  });
}
