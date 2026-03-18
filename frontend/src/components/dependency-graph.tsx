"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { ArrowRight, GitBranch, LayoutGrid, Network } from "lucide-react";
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
}

interface DependencyGraphProps {
  dependencies?: Dependency[];
  sections?: Section[];
  className?: string;
  onSectionClick?: (slug: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  approved: "#22c55e",
  in_progress: "#3b82f6",
  review: "#f59e0b",
  draft: "#9496ad",
  outdated: "#ef4444",
};

const TYPE_COLORS: Record<string, string> = {
  references: "#6366f1",
  implements: "#22c55e",
  blocks: "#ef4444",
  extends: "#a855f7",
};

// --- List View ---
function ListView({
  dependencies,
  sections,
  onSectionClick,
}: {
  dependencies: Dependency[];
  sections: Section[];
  onSectionClick?: (slug: string) => void;
}) {
  const sectionMap = new Map(sections.map((s) => [s.slug, s]));
  const getTitle = (slug: string) => sectionMap.get(slug)?.title || slug;
  const getStatus = (slug: string) => sectionMap.get(slug)?.status || "draft";

  const grouped = new Map<string, Dependency[]>();
  for (const dep of dependencies) {
    if (!grouped.has(dep.from_slug)) grouped.set(dep.from_slug, []);
    grouped.get(dep.from_slug)!.push(dep);
  }

  return (
    <div className="space-y-3">
      {Array.from(grouped.entries()).map(([fromSlug, deps]) => (
        <div key={fromSlug} className="rounded-lg border p-4">
          <button
            className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors"
            onClick={() => onSectionClick?.(fromSlug)}
          >
            <div
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ background: STATUS_COLORS[getStatus(fromSlug)] || "#9496ad" }}
            />
            {getTitle(fromSlug)}
          </button>
          <div className="mt-2 space-y-1.5 pl-5">
            {deps.map((dep, i) => {
              const depType = dep.dependency_type || dep.type || "references";
              return (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <ArrowRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <Badge
                    variant="outline"
                    className="text-xs border"
                    style={{ borderColor: TYPE_COLORS[depType] || "#44465a", color: TYPE_COLORS[depType] || "#9496ad" }}
                  >
                    {depType}
                  </Badge>
                  <button
                    className="text-muted-foreground hover:text-primary transition-colors"
                    onClick={() => onSectionClick?.(dep.to_slug)}
                  >
                    {getTitle(dep.to_slug)}
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
  slug: string;
  title: string;
  status: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  width: number;
}

function GraphView({
  dependencies,
  sections,
  onSectionClick,
}: {
  dependencies: Dependency[];
  sections: Section[];
  onSectionClick?: (slug: string) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [nodes, setNodes] = useState<GNode[]>([]);
  const [dragging, setDragging] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const frameRef = useRef(0);
  const iterRef = useRef(0);

  const W = 1000;
  const H = 650;

  useEffect(() => {
    if (sections.length === 0) return;
    const initial: GNode[] = sections.map((s, i) => {
      const angle = (2 * Math.PI * i) / sections.length;
      const r = Math.min(W, H) * 0.3;
      const titleW = Math.min(s.title.length * 7 + 24, 160);
      return {
        slug: s.slug,
        title: s.title,
        status: s.status,
        x: W / 2 + r * Math.cos(angle),
        y: H / 2 + r * Math.sin(angle),
        vx: 0,
        vy: 0,
        width: titleW,
      };
    });
    iterRef.current = 0;
    setNodes(initial);
  }, [sections]);

  useEffect(() => {
    if (nodes.length === 0) return;

    const tick = () => {
      if (iterRef.current > 300) return;
      iterRef.current++;

      setNodes((prev) => {
        const ns = prev.map((n) => ({ ...n }));

        // Repulsion
        for (let i = 0; i < ns.length; i++) {
          for (let j = i + 1; j < ns.length; j++) {
            const dx = ns[j].x - ns[i].x;
            const dy = ns[j].y - ns[i].y;
            const d = Math.max(Math.sqrt(dx * dx + dy * dy), 10);
            const f = 12000 / (d * d);
            ns[i].vx -= (dx / d) * f;
            ns[i].vy -= (dy / d) * f;
            ns[j].vx += (dx / d) * f;
            ns[j].vy += (dy / d) * f;
          }
        }

        // Attraction along edges
        for (const dep of dependencies) {
          const a = ns.find((n) => n.slug === dep.from_slug);
          const b = ns.find((n) => n.slug === dep.to_slug);
          if (!a || !b) continue;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const d = Math.max(Math.sqrt(dx * dx + dy * dy), 10);
          const f = (d - 180) * 0.03;
          a.vx += (dx / d) * f;
          a.vy += (dy / d) * f;
          b.vx -= (dx / d) * f;
          b.vy -= (dy / d) * f;
        }

        // Center gravity
        for (const n of ns) {
          n.vx += (W / 2 - n.x) * 0.008;
          n.vy += (H / 2 - n.y) * 0.008;
        }

        // Apply
        for (const n of ns) {
          if (n.slug === dragging) continue;
          n.vx *= 0.6;
          n.vy *= 0.6;
          n.x = Math.max(80, Math.min(W - 80, n.x + n.vx));
          n.y = Math.max(30, Math.min(H - 30, n.y + n.vy));
        }
        return ns;
      });

      if (iterRef.current <= 300) {
        frameRef.current = requestAnimationFrame(tick);
      }
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [nodes.length, dependencies, dragging]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragging || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const scaleX = W / rect.width;
      const scaleY = H / rect.height;
      const x = (e.clientX - rect.left) * scaleX;
      const y = (e.clientY - rect.top) * scaleY;
      setNodes((prev) =>
        prev.map((n) => (n.slug === dragging ? { ...n, x, y, vx: 0, vy: 0 } : n))
      );
    },
    [dragging]
  );

  // Edges connected to hovered node
  const hoveredEdges = useMemo(() => {
    if (!hovered) return new Set<number>();
    const set = new Set<number>();
    dependencies.forEach((d, i) => {
      if (d.from_slug === hovered || d.to_slug === hovered) set.add(i);
    });
    return set;
  }, [hovered, dependencies]);

  const nodeMap = new Map(nodes.map((n) => [n.slug, n]));

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      className="w-full rounded-lg border bg-card"
      onMouseMove={handleMouseMove}
      onMouseUp={() => setDragging(null)}
      onMouseLeave={() => setDragging(null)}
    >
      <defs>
        <marker id="arrow" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#6366f1" />
        </marker>
        <marker id="arrow-hi" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#f59e0b" />
        </marker>
      </defs>

      {/* Edges */}
      {dependencies.map((dep, i) => {
        const from = nodeMap.get(dep.from_slug);
        const to = nodeMap.get(dep.to_slug);
        if (!from || !to) return null;
        const hi = hoveredEdges.has(i);
        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        const nx = dx / d;
        const ny = dy / d;
        // Elliptical offset: wider on x-axis (pill shape)
        const fromR = Math.sqrt((from.width/2 * nx) ** 2 + (16 * ny) ** 2) + 2;
        const toR = Math.sqrt((to.width/2 * nx) ** 2 + (16 * ny) ** 2) + 12;
        return (
          <line
            key={i}
            x1={from.x + nx * fromR}
            y1={from.y + ny * fromR}
            x2={to.x - nx * toR}
            y2={to.y - ny * toR}
            stroke={hi ? "#f59e0b" : "#6366f1"}
            strokeWidth={hi ? 2.5 : 1.5}
            opacity={hovered ? (hi ? 1 : 0.15) : 0.45}
            markerEnd={hi ? "url(#arrow-hi)" : "url(#arrow)"}
          />
        );
      })}

      {/* Nodes */}
      {nodes.map((node) => {
        const color = STATUS_COLORS[node.status] || "#9496ad";
        const isHovered = hovered === node.slug;
        const dimmed = hovered && !isHovered && !hoveredEdges.size;
        return (
          <g
            key={node.slug}
            onMouseDown={(e) => { e.preventDefault(); setDragging(node.slug); }}
            onMouseEnter={() => setHovered(node.slug)}
            onMouseLeave={() => setHovered(null)}
            onClick={() => onSectionClick?.(node.slug)}
            style={{ cursor: "pointer" }}
            opacity={dimmed ? 0.3 : 1}
          >
            <rect
              x={node.x - node.width / 2}
              y={node.y - 16}
              width={node.width}
              height={32}
              rx={16}
              fill={color}
              stroke={isHovered ? "#ffffff" : "transparent"}
              strokeWidth={2}
            />
            <text
              x={node.x}
              y={node.y + 5}
              textAnchor="middle"
              fill="white"
              fontSize={11}
              fontWeight={600}
              fontFamily="Inter, sans-serif"
            >
              {node.title.length > 18 ? node.title.slice(0, 17) + "…" : node.title}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// --- Main Component with Toggle ---
export function DependencyGraph({
  dependencies = [],
  sections = [],
  className,
  onSectionClick,
}: DependencyGraphProps) {
  const [view, setView] = useState<"graph" | "list">("graph");

  if (sections.length === 0 || dependencies.length === 0) {
    return (
      <div className={cn("flex flex-col items-center justify-center rounded-lg border border-dashed p-12 text-center", className)}>
        <GitBranch className="h-10 w-10 text-muted-foreground/50 mb-3" />
        <h3 className="text-sm font-semibold">No Dependencies</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Add dependencies between sections to see them here.
        </p>
      </div>
    );
  }

  return (
    <div className={cn("max-w-5xl mx-auto space-y-4", className)}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Dependencies</h3>
          <p className="text-xs text-muted-foreground">
            {dependencies.length} edges across {sections.length} sections
            {view === "graph" && " — hover a node to highlight connections, drag to rearrange"}
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-lg border p-1">
          <Button
            variant={view === "graph" ? "secondary" : "ghost"}
            size="sm"
            className="h-7 px-2.5"
            onClick={() => setView("graph")}
          >
            <Network className="h-3.5 w-3.5 mr-1" />
            Graph
          </Button>
          <Button
            variant={view === "list" ? "secondary" : "ghost"}
            size="sm"
            className="h-7 px-2.5"
            onClick={() => setView("list")}
          >
            <LayoutGrid className="h-3.5 w-3.5 mr-1" />
            List
          </Button>
        </div>
      </div>

      {view === "graph" && (
        <div>
          <div className="flex gap-3 mb-2">
            {Object.entries(STATUS_COLORS).map(([status, color]) => (
              <div key={status} className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
                <span className="text-xs text-muted-foreground capitalize">{status.replace("_", " ")}</span>
              </div>
            ))}
          </div>
          <GraphView dependencies={dependencies} sections={sections} onSectionClick={onSectionClick} />
        </div>
      )}

      {view === "list" && (
        <ListView dependencies={dependencies} sections={sections} onSectionClick={onSectionClick} />
      )}
    </div>
  );
}
