"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";

export function Header() {
  return (
    <header
      className={cn(
        "sticky top-0 z-50 w-full h-[60px]",
        "bg-[rgba(8,13,24,0.92)] backdrop-blur-[12px]",
        "border-b border-border"
      )}
    >
      <div className="container h-full flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 shrink-0">
          <div className="w-8 h-8 rounded bg-primary/20 border border-primary/40 flex items-center justify-center">
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              className="text-primary"
            >
              <path
                d="M8 1L14 4.5V11.5L8 15L2 11.5V4.5L8 1Z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
              <path
                d="M8 5L11 6.75V10.25L8 12L5 10.25V6.75L8 5Z"
                fill="currentColor"
                opacity="0.6"
              />
            </svg>
          </div>
          <div className="hidden sm:flex flex-col">
            <span className="font-heading text-sm font-bold text-foreground leading-tight">
              Software Archaeologist
            </span>
            <span className="font-code text-[9px] uppercase tracking-[0.1em] text-muted-foreground leading-tight">
              Multi-Agent System
            </span>
          </div>
        </Link>

        {/* Status badge */}
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#10B981] shadow-[0_0_6px_#10B981] animate-status-pulse" />
          <span className="font-code text-[10px] uppercase tracking-[0.08em] text-[#10B981]">
            Activo
          </span>
        </div>
      </div>
    </header>
  );
}
