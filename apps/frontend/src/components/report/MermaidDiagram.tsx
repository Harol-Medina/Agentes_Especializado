"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { cn } from "@/lib/utils";

interface MermaidDiagramProps {
  /** Mermaid syntax string to render */
  chart: string;
  /** Diagram title shown above */
  title?: string;
  /** Unique ID for the diagram (avoids Mermaid ID collisions) */
  id?: string;
}

/**
 * Renders a Mermaid diagram with dark theme styling.
 * Includes export buttons for PNG and SVG.
 */
export function MermaidDiagram({ chart, title, id }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [isRendering, setIsRendering] = useState(true);

  const diagramId = id || `mermaid-${Math.random().toString(36).slice(2, 9)}`;

  useEffect(() => {
    if (!chart || !containerRef.current) return;

    let cancelled = false;

    async function renderDiagram() {
      setIsRendering(true);
      setError("");

      try {
        // Dynamic import — mermaid is heavy, load only when needed
        const mermaid = (await import("mermaid")).default;

        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          themeVariables: {
            primaryColor: "#F59E0B",
            primaryTextColor: "#080D18",
            primaryBorderColor: "#F59E0B",
            lineColor: "#1E2D45",
            secondaryColor: "#06B6D4",
            tertiaryColor: "#0F1624",
            background: "#080D18",
            mainBkg: "#0F1624",
            nodeBorder: "#1E2D45",
            clusterBkg: "#0F1624",
            clusterBorder: "#1E2D45",
            titleColor: "#F0F4FF",
            edgeLabelBackground: "#0F1624",
            textColor: "#E2E8F0",
          },
          flowchart: {
            htmlLabels: true,
            curve: "basis",
          },
          securityLevel: "loose",
        });

        const { svg } = await mermaid.render(diagramId, chart);

        if (!cancelled) {
          setSvgContent(svg);
          setIsRendering(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to render diagram");
          setIsRendering(false);
        }
      }
    }

    renderDiagram();

    return () => {
      cancelled = true;
    };
  }, [chart, diagramId]);

  const handleExportSVG = useCallback(() => {
    if (!svgContent) return;
    const blob = new Blob([svgContent], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title || "diagram"}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  }, [svgContent, title]);

  const handleExportPNG = useCallback(async () => {
    if (!svgContent || !containerRef.current) return;

    const svgEl = containerRef.current.querySelector("svg");
    if (!svgEl) return;

    const canvas = document.createElement("canvas");
    const bbox = svgEl.getBoundingClientRect();
    canvas.width = bbox.width * 2;
    canvas.height = bbox.height * 2;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.scale(2, 2);

    const img = new Image();
    const svgBlob = new Blob([svgContent], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(svgBlob);

    img.onload = () => {
      ctx.fillStyle = "#080D18";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, bbox.width, bbox.height);
      URL.revokeObjectURL(url);

      const pngUrl = canvas.toDataURL("image/png");
      const a = document.createElement("a");
      a.href = pngUrl;
      a.download = `${title || "diagram"}.png`;
      a.click();
    };

    img.src = url;
  }, [svgContent, title]);

  // ─── Render states ───

  if (isRendering) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        {title && (
          <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-4">
            {title}
          </h4>
        )}
        <div className="flex items-center justify-center gap-2 py-8 text-muted-foreground">
          <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="font-sans text-sm">Rendering diagram...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card border border-border rounded-lg p-6">
        {title && (
          <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground mb-4">
            {title}
          </h4>
        )}
        <div className="bg-[#EF444410] border border-[#EF444430] rounded p-3">
          <p className="font-code text-[11px] text-[#EF4444]">Diagram render error: {error}</p>
        </div>
        {/* Show raw source as fallback */}
        <details className="mt-3">
          <summary className="font-code text-[10px] text-muted-foreground cursor-pointer hover:text-foreground">
            Show raw Mermaid source
          </summary>
          <pre className="mt-2 font-code text-[11px] text-muted-foreground bg-muted/30 rounded p-3 overflow-x-auto">
            {chart}
          </pre>
        </details>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        {title && (
          <h4 className="font-code text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
            {title}
          </h4>
        )}
        <div className="flex gap-2">
          <button
            onClick={handleExportSVG}
            className={cn(
              "font-code text-[10px] uppercase tracking-wider",
              "px-2.5 py-1 rounded border border-border",
              "text-muted-foreground hover:text-foreground hover:border-muted-foreground",
              "transition-colors duration-150"
            )}
          >
            SVG
          </button>
          <button
            onClick={handleExportPNG}
            className={cn(
              "font-code text-[10px] uppercase tracking-wider",
              "px-2.5 py-1 rounded border border-border",
              "text-muted-foreground hover:text-foreground hover:border-muted-foreground",
              "transition-colors duration-150"
            )}
          >
            PNG
          </button>
        </div>
      </div>

      {/* Diagram */}
      <div
        ref={containerRef}
        className="overflow-x-auto [&_svg]:max-w-full [&_svg]:h-auto"
        dangerouslySetInnerHTML={{ __html: svgContent }}
      />
    </div>
  );
}
