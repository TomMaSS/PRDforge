"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { ArrowRight, LayoutGrid, Network, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Dependency {
  from_slug: string;
  to_slug: string;
  type?: string;
  dependency_type?: string;
  description?: string;
}

interface Section {
  slug: string;
  title: string;
  status: string;
  summary?: string;
  word_count?: number;
}

interface DependencyGraphProps {
  dependencies?: Dependency[];
  sections?: Section[];
  className?: string;
  onSectionClick?: (slug: string) => void;
}

const DEP_TYPE_COLORS: Record<string, string> = {
  references: "#6366f1",
  implements: "#22c55e",
  blocks: "#ef6b6b",
  extends: "#38bdf8",
};

const STATUS_COLORS: Record<string, string> = {
  approved: "#22c55e",
  in_progress: "#3b82f6",
  review: "#f59e0b",
  draft: "#9496ad",
  outdated: "#ef4444",
};

// --- List View ---
function ListView({ dependencies, sections, onSectionClick }: {
  dependencies: Dependency[]; sections: Section[]; onSectionClick?: (slug: string) => void;
}) {
  const sectionMap = new Map(sections.map((s) => [s.slug, s]));
  const grouped = new Map<string, Dependency[]>();
  for (const dep of dependencies) {
    if (!grouped.has(dep.from_slug)) grouped.set(dep.from_slug, []);
    grouped.get(dep.from_slug)!.push(dep);
  }
  return (
    <div className="space-y-3">
      {Array.from(grouped.entries()).map(([fromSlug, deps]) => (
        <div key={fromSlug} className="rounded-lg border p-4">
          <button className="flex items-center gap-2 text-sm font-medium hover:text-primary" onClick={() => onSectionClick?.(fromSlug)}>
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: STATUS_COLORS[sectionMap.get(fromSlug)?.status || "draft"] }} />
            {sectionMap.get(fromSlug)?.title || fromSlug}
          </button>
          <div className="mt-2 space-y-1.5 pl-5">
            {deps.map((dep, i) => {
              const t = dep.dependency_type || dep.type || "references";
              return (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <ArrowRight className="h-3.5 w-3.5 shrink-0" style={{ color: DEP_TYPE_COLORS[t] || "#6366f1" }} />
                  <Badge variant="outline" className="text-xs" style={{ borderColor: DEP_TYPE_COLORS[t], color: DEP_TYPE_COLORS[t] }}>{t}</Badge>
                  <button className="text-muted-foreground hover:text-primary" onClick={() => onSectionClick?.(dep.to_slug)}>
                    {sectionMap.get(dep.to_slug)?.title || dep.to_slug}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// --- Graph View ---
interface GNode {
  slug: string; title: string; status: string; summary: string; wordCount: number;
  x: number; y: number; vx: number; vy: number; r: number;
}

function wrapText(text: string, maxCharsPerLine: number): string[] {
  const words = text.split(" ");
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    if (current.length + word.length + 1 > maxCharsPerLine && current) {
      lines.push(current);
      current = word;
    } else {
      current = current ? current + " " + word : word;
    }
  }
  if (current) lines.push(current);
  // Max 3 lines, truncate last
  if (lines.length > 3) {
    lines.length = 3;
    lines[2] = lines[2].slice(0, maxCharsPerLine - 3) + "...";
  }
  return lines;
}

function GraphView({ dependencies, sections, onSectionClick }: {
  dependencies: Dependency[]; sections: Section[]; onSectionClick?: (slug: string) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [nodes, setNodes] = useState<GNode[]>([]);
  const [dragging, setDragging] = useState<string | null>(null);
  const [popup, setPopup] = useState<GNode | null>(null);
  const frameRef = useRef(0);
  const iterRef = useRef(0);

  const W = 1000, H = 700;
  const NODE_R = 42;

  useEffect(() => {
    if (!sections.length) return;
    const init: GNode[] = sections.map((s, i) => {
      const angle = (2 * Math.PI * i) / sections.length;
      const r = Math.min(W, H) * 0.3;
      return {
        slug: s.slug, title: s.title, status: s.status,
        summary: s.summary || "", wordCount: s.word_count || 0,
        x: W / 2 + r * Math.cos(angle), y: H / 2 + r * Math.sin(angle),
        vx: 0, vy: 0, r: NODE_R,
      };
    });
    iterRef.current = 0;
    setNodes(init);
  }, [sections]);

  useEffect(() => {
    if (!nodes.length) return;
    const tick = () => {
      if (iterRef.current > 350) return;
      iterRef.current++;
      setNodes((prev) => {
        const ns = prev.map((n) => ({ ...n }));
        // Repulsion
        for (let i = 0; i < ns.length; i++) {
          for (let j = i + 1; j < ns.length; j++) {
            const dx = ns[j].x - ns[i].x, dy = ns[j].y - ns[i].y;
            const d = Math.max(Math.sqrt(dx * dx + dy * dy), 10);
            const f = 15000 / (d * d);
            ns[i].vx -= (dx / d) * f; ns[i].vy -= (dy / d) * f;
            ns[j].vx += (dx / d) * f; ns[j].vy += (dy / d) * f;
          }
        }
        // Edge attraction
        for (const dep of dependencies) {
          const a = ns.find((n) => n.slug === dep.from_slug);
          const b = ns.find((n) => n.slug === dep.to_slug);
          if (!a || !b) continue;
          const dx = b.x - a.x, dy = b.y - a.y;
          const d = Math.max(Math.sqrt(dx * dx + dy * dy), 10);
          const f = (d - 160) * 0.025;
          a.vx += (dx / d) * f; a.vy += (dy / d) * f;
          b.vx -= (dx / d) * f; b.vy -= (dy / d) * f;
        }
        // Center gravity
        for (const n of ns) { n.vx += (W / 2 - n.x) * 0.006; n.vy += (H / 2 - n.y) * 0.006; }
        // Apply
        for (const n of ns) {
          if (n.slug === dragging) continue;
          n.vx *= 0.55; n.vy *= 0.55;
          n.x = Math.max(NODE_R + 10, Math.min(W - NODE_R - 10, n.x + n.vx));
          n.y = Math.max(NODE_R + 10, Math.min(H - NODE_R - 10, n.y + n.vy));
        }
        return ns;
      });
      if (iterRef.current <= 350) frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [nodes.length, dependencies, dragging]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (W / rect.width);
    const y = (e.clientY - rect.top) * (H / rect.height);
    setNodes((prev) => prev.map((n) => n.slug === dragging ? { ...n, x, y, vx: 0, vy: 0 } : n));
  }, [dragging]);

  const nodeMap = new Map(nodes.map((n) => [n.slug, n]));

  // Curved path between two nodes
  const edgePath = (from: GNode, to: GNode): string => {
    const dx = to.x - from.x, dy = to.y - from.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 1;
    const nx = dx / d, ny = dy / d;
    // Start/end at circle edge
    const x1 = from.x + nx * from.r, y1 = from.y + ny * from.r;
    const x2 = to.x - nx * to.r, y2 = to.y - ny * to.r;
    // Control point offset perpendicular for curve
    const cx = (x1 + x2) / 2 - ny * 25;
    const cy = (y1 + y2) / 2 + nx * 25;
    return `M${x1},${y1} Q${cx},${cy} ${x2},${y2}`;
  };

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="w-full rounded-lg border bg-card"
        onMouseMove={handleMouseMove}
        onMouseUp={() => setDragging(null)}
        onMouseLeave={() => setDragging(null)}
      >
        <defs>
          {Object.entries(DEP_TYPE_COLORS).map(([type, color]) => (
            <marker key={type} id={`arrow-${type}`} markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0.5, 9 3.5, 0 6.5" fill={color} />
            </marker>
          ))}
        </defs>

        {/* Edges — curved paths with colored arrows */}
        {dependencies.map((dep, i) => {
          const from = nodeMap.get(dep.from_slug);
          const to = nodeMap.get(dep.to_slug);
          if (!from || !to) return null;
          const t = dep.dependency_type || dep.type || "references";
          const color = DEP_TYPE_COLORS[t] || "#6366f1";
          return (
            <path
              key={i}
              d={edgePath(from, to)}
              fill="none"
              stroke={color}
              strokeWidth={2}
              opacity={0.6}
              markerEnd={`url(#arrow-${t})`}
            />
          );
        })}

        {/* Nodes — circles with multi-line text */}
        {nodes.map((node) => {
          const lines = wrapText(node.title, 12);
          return (
            <g
              key={node.slug}
              onMouseDown={(e) => { e.preventDefault(); setDragging(node.slug); }}
              onClick={() => setPopup(popup?.slug === node.slug ? null : node)}
              style={{ cursor: "pointer" }}
            >
              <circle
                cx={node.x} cy={node.y} r={node.r}
                fill="#3d3f4a" stroke="#5a5c6a" strokeWidth={2}
              />
              {lines.map((line, li) => (
                <text
                  key={li}
                  x={node.x} y={node.y + (li - (lines.length - 1) / 2) * 13 + 4}
                  textAnchor="middle" fill="#e2e4ea" fontSize={10.5}
                  fontWeight={600} fontFamily="Inter, sans-serif"
                >
                  {line}
                </text>
              ))}
            </g>
          );
        })}
      </svg>

      {/* Popup card */}
      {popup && (
        <div
          className="absolute bg-card border rounded-lg shadow-xl p-4 w-64 z-10"
          style={{
            left: `${(popup.x / W) * 100}%`,
            top: `${(popup.y / H) * 100}%`,
            transform: "translate(-50%, -120%)",
          }}
        >
          <div className="flex items-start justify-between mb-2">
            <button
              className="text-sm font-semibold text-primary hover:underline"
              onClick={() => { onSectionClick?.(popup.slug); setPopup(null); }}
            >
              {popup.title}
            </button>
            <div className="flex items-center gap-2">
              <button
                className="text-xs text-muted-foreground hover:text-primary"
                onClick={() => { onSectionClick?.(popup.slug); setPopup(null); }}
              >
                Open →
              </button>
              <button onClick={() => setPopup(null)}>
                <X className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
            </div>
          </div>
          {popup.summary && (
            <p className="text-xs text-muted-foreground mb-2 line-clamp-3">{popup.summary}</p>
          )}
          <div className="flex gap-2 text-xs text-muted-foreground">
            <span>{popup.status}</span>
            {popup.wordCount > 0 && <span>{popup.wordCount} words</span>}
          </div>
        </div>
      )}
    </div>
  );
}

// --- Main Component ---
export function DependencyGraph({ dependencies = [], sections = [], className, onSectionClick }: DependencyGraphProps) {
  const [view, setView] = useState<"graph" | "list">("graph");

  if (!sections.length || !dependencies.length) {
    return (
      <div className={cn("flex flex-col items-center justify-center rounded-lg border border-dashed p-12 text-center", className)}>
        <h3 className="text-sm font-semibold">No Dependencies</h3>
        <p className="mt-1 text-xs text-muted-foreground">Add dependencies between sections to see them here.</p>
      </div>
    );
  }

  return (
    <div className={cn("max-w-5xl mx-auto space-y-4", className)}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Dependencies</h3>
          <p className="text-xs text-muted-foreground">
            {dependencies.length} edges · {sections.length} sections
            {view === "graph" && " — click node for details, drag to rearrange"}
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-lg border p-1">
          <Button variant={view === "graph" ? "secondary" : "ghost"} size="sm" className="h-7 px-2.5" onClick={() => setView("graph")}>
            <Network className="h-3.5 w-3.5 mr-1" />Graph
          </Button>
          <Button variant={view === "list" ? "secondary" : "ghost"} size="sm" className="h-7 px-2.5" onClick={() => setView("list")}>
            <LayoutGrid className="h-3.5 w-3.5 mr-1" />List
          </Button>
        </div>
      </div>

      {view === "graph" && (
        <div>
          <div className="flex gap-4 mb-2">
            {Object.entries(DEP_TYPE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5">
                <div className="w-6 h-0.5" style={{ background: color }} />
                <span className="text-xs text-muted-foreground capitalize">{type}</span>
              </div>
            ))}
          </div>
          <GraphView dependencies={dependencies} sections={sections} onSectionClick={onSectionClick} />
        </div>
      )}

      {view === "list" && <ListView dependencies={dependencies} sections={sections} onSectionClick={onSectionClick} />}
    </div>
  );
}
