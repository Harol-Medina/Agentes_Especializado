"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { useState } from "react";

const navItems = [
  { label: "Dashboard", href: "/", active: true },
  { label: "Proyectos", href: "#proyectos", active: false },
  { label: "Agentes", href: "#agentes", active: false },
  { label: "Pipeline", href: "#pipeline", active: false },
  { label: "Exportar", href: "#exportar", active: false },
];

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "font-sans text-[13px] px-3 py-1.5 rounded transition-colors duration-150",
                item.active
                  ? "text-primary font-semibold border-b-2 border-primary"
                  : "text-muted-foreground hover:text-foreground font-normal"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Right side: status + action */}
        <div className="flex items-center gap-3">
          {/* Status badge */}
          <div className="hidden sm:flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#10B981] shadow-[0_0_6px_#10B981] animate-status-pulse" />
            <span className="font-code text-[10px] uppercase tracking-[0.08em] text-[#10B981]">
              Activo
            </span>
          </div>

          {/* New project button */}
          <Link
            href="/"
            className={cn(
              "font-sans text-[12px] font-bold tracking-[0.04em]",
              "bg-primary text-primary-foreground",
              "px-3.5 py-2 rounded",
              "hover:bg-primary/90 transition-colors duration-150",
              "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:ring-offset-background"
            )}
          >
            + Nuevo Proyecto
          </Link>

          {/* Mobile menu button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-1.5 text-muted-foreground hover:text-foreground"
            aria-label="Toggle menu"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              {mobileMenuOpen ? (
                <path d="M5 5L15 15M15 5L5 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              ) : (
                <>
                  <path d="M3 5H17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M3 10H17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M3 15H17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </>
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="md:hidden absolute top-[60px] left-0 right-0 bg-[rgba(8,13,24,0.98)] backdrop-blur-[12px] border-b border-border p-4 animate-fade-in">
          <nav className="flex flex-col gap-2">
            {navItems.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  "font-sans text-[14px] px-3 py-2 rounded transition-colors duration-150",
                  item.active
                    ? "text-primary font-semibold bg-primary/10"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      )}
    </header>
  );
}
