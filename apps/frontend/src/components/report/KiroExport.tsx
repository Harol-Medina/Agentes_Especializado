"use client";

import { useKiroExport } from "@/hooks/useKiroExport";
import { cn } from "@/lib/utils";
import { useState } from "react";

// ─────────────────────────────────────────────
// Markdown Preview — basic syntax highlighting
// ─────────────────────────────────────────────

function MarkdownPreview({ content }: { content: string }) {
  const lines = content.split("\n");

  return (
    <pre className="whitespace-pre-wrap break-words text-sm font-mono leading-relaxed">
      {lines.map((line, i) => {
        // Code block lines
        if (line.startsWith("```")) {
          return (
            <span key={i} className="text-muted-foreground">
              {line}
              {"\n"}
            </span>
          );
        }

        // H1
        if (line.startsWith("# ")) {
          return (
            <span key={i} className="text-primary font-bold text-base">
              {line}
              {"\n"}
            </span>
          );
        }

        // H2
        if (line.startsWith("## ")) {
          return (
            <span key={i} className="text-primary font-bold text-sm">
              {line}
              {"\n"}
            </span>
          );
        }

        // H3
        if (line.startsWith("### ")) {
          return (
            <span key={i} className="text-primary font-bold text-xs">
              {line}
              {"\n"}
            </span>
          );
        }

        // YAML frontmatter delimiter
        if (line.startsWith("---")) {
          return (
            <span key={i} className="text-muted-foreground">
              {line}
              {"\n"}
            </span>
          );
        }

        // Task list items
        if (line.startsWith("- [ ]") || line.startsWith("- [x]")) {
          return (
            <span key={i} className="text-card-foreground">
              {line}
              {"\n"}
            </span>
          );
        }

        // List items
        if (line.startsWith("- ")) {
          return (
            <span key={i} className="text-card-foreground">
              {line}
              {"\n"}
            </span>
          );
        }

        // Default text
        return (
          <span key={i} className="text-card-foreground">
            {line}
            {"\n"}
          </span>
        );
      })}
    </pre>
  );
}

// ─────────────────────────────────────────────
// KiroExport Component
// ─────────────────────────────────────────────

interface KiroExportProps {
  projectId: string;
}

export function KiroExport({ projectId }: KiroExportProps) {
  const { markdown, isLoading, error } = useKiroExport(projectId);
  const [copied, setCopied] = useState(false);

  const handleDownload = () => {
    if (!markdown) return;
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "modernization-spec.md";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopy = async () => {
    if (!markdown) return;
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = markdown;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="container py-10">
        <div className="flex flex-col items-center justify-center gap-4 py-20">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-muted-foreground text-sm font-body">
            Loading Kiro spec...
          </p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="container py-10">
        <div className="bg-card border border-border rounded-xl p-6 text-center">
          <p className="text-[#EF4444] font-mono text-sm mb-2">
            Failed to load Kiro spec
          </p>
          <p className="text-muted-foreground text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container py-8">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-display text-xl font-bold text-foreground">
          Kiro Spec Export
        </h2>

        <div className="flex items-center gap-3">
          {/* Copy button */}
          <button
            onClick={handleCopy}
            className={cn(
              "px-4 py-2 rounded-md text-xs font-semibold tracking-wide",
              "border border-border text-muted-foreground",
              "hover:border-primary/40 hover:text-foreground",
              "transition-colors duration-150",
              "focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
            )}
          >
            {copied ? "Copied!" : "Copy"}
          </button>

          {/* Download button */}
          <button
            onClick={handleDownload}
            className={cn(
              "px-4 py-2 rounded-md text-xs font-bold tracking-wide",
              "bg-primary text-primary-foreground",
              "hover:bg-primary/90",
              "transition-colors duration-150",
              "focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
            )}
          >
            Download .md
          </button>
        </div>
      </div>

      {/* Markdown preview */}
      <div
        className={cn(
          "bg-card border border-border rounded-xl p-6",
          "max-h-[calc(100vh-220px)] overflow-y-auto"
        )}
      >
        {markdown ? (
          <MarkdownPreview content={markdown} />
        ) : (
          <p className="text-muted-foreground text-sm text-center py-10">
            No Kiro spec available for this project.
          </p>
        )}
      </div>
    </div>
  );
}
