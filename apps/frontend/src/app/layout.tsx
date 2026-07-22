import type { Metadata } from "next";
import { Roboto_Slab, Inter, JetBrains_Mono } from "next/font/google";
import "@/styles/globals.css";

// ─────────────────────────────────────────────
// Google Fonts
// ─────────────────────────────────────────────

const robotoSlab = Roboto_Slab({
  subsets: ["latin"],
  weight: ["300", "400", "600", "700"],
  variable: "--font-display",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

// ─────────────────────────────────────────────
// Metadata
// ─────────────────────────────────────────────

export const metadata: Metadata = {
  title: {
    template: "%s | Software Archaeologist",
    default: "Software Archaeologist",
  },
  description:
    "Analyze public GitHub repositories with AI-powered agents. Generate dependency graphs, architecture reports, and Kiro specs.",
  keywords: ["software analysis", "architecture", "dependency graph", "AI", "code review"],
};

// ─────────────────────────────────────────────
// Root Layout
// ─────────────────────────────────────────────

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`dark ${robotoSlab.variable} ${inter.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body className="bg-background text-foreground font-body antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
