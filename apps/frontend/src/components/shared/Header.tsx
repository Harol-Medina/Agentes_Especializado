"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";

const navItems = [
  { label: "Analyze", href: "/", active: true },
  { label: "Docs", href: "#", active: false },
];

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
        <Link href="/" className="flex items-center gap-2">
          <span className="font-display text-base font-bold text-foreground tracking-tight">
            Software Archaeologist
          </span>
        </Link>

        {/* Nav */}
        <nav className="flex items-center gap-6">
          {navItems.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "font-body text-[13px] transition-colors duration-150",
                item.active
                  ? "text-primary font-semibold border-b-2 border-primary pb-0.5"
                  : "text-muted-foreground hover:text-foreground font-normal"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
