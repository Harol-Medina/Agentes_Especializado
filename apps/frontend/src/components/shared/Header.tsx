"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/" },
  { label: "Proyectos", href: "/projects" },
  { label: "Agentes", href: "/agents" },
  { label: "Pipeline", href: "/pipeline" },
  { label: "Exportar", href: "/export" },
];

export function Header() {
  const pathname = usePathname();

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
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-primary/20 border border-primary/40 flex items-center justify-center">
              <span className="font-display text-xs font-bold text-primary">K</span>
            </div>
            <div className="flex flex-col">
              <span className="font-display text-sm font-bold text-foreground leading-none">
                Software Archaeologist
              </span>
              <span className="font-mono text-[9px] uppercase tracking-[0.1em] text-muted-foreground">
                Multi-Agent System
              </span>
            </div>
          </Link>
        </div>

        {/* Nav Tabs */}
        <nav className="flex items-center gap-1" role="tablist">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.label}
                href={item.href}
                role="tab"
                aria-selected={isActive}
                className={cn(
                  "px-3 py-1.5 rounded-[4px] font-body text-[13px] transition-colors duration-150",
                  isActive
                    ? "text-primary font-semibold bg-primary/10"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#10B981] shadow-[0_0_6px_#10B981]" />
            <span className="font-mono text-[10px] uppercase tracking-[0.08em] text-[#10B981]">
              Activo
            </span>
          </span>
          <Link
            href="/"
            className={cn(
              "px-3 py-1.5 rounded-[4px]",
              "bg-primary text-primary-foreground",
              "font-body text-[12px] font-bold",
              "hover:opacity-90 transition-opacity duration-150"
            )}
          >
            + Nuevo Proyecto
          </Link>
        </div>
      </div>
    </header>
  );
}
