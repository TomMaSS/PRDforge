"use client";

import { useState, useMemo } from "react";
import { ChevronDown, ChevronRight, Plus, Settings, BookOpen, Archive } from "lucide-react";
import { StatusDot } from "@/components/status-dot";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { SectionListItem } from "@/lib/types";

interface SectionSidebarProps {
  sections: SectionListItem[];
  activeSlug?: string;
  onSelect: (slug: string) => void;
  projectName?: string;
  projectVersion?: number;
  projectSlug?: string;
  onNavigateSettings?: () => void;
}

interface TreeNode extends SectionListItem {
  children: TreeNode[];
}

function buildTree(sections: SectionListItem[]): TreeNode[] {
  const map = new Map<string, TreeNode>();
  const roots: TreeNode[] = [];

  // Create tree nodes
  for (const s of sections) {
    map.set(s.slug, { ...s, children: [] });
  }

  // Build hierarchy
  for (const s of sections) {
    const node = map.get(s.slug)!;
    if (s.parent_slug && map.has(s.parent_slug)) {
      map.get(s.parent_slug)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

function SectionTreeItem({
  node,
  depth,
  activeSlug,
  onSelect,
  expandedSlugs,
  toggleExpand,
}: {
  node: TreeNode;
  depth: number;
  activeSlug?: string;
  onSelect: (slug: string) => void;
  expandedSlugs: Set<string>;
  toggleExpand: (slug: string) => void;
}) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expandedSlugs.has(node.slug);
  const isActive = activeSlug === node.slug;

  return (
    <>
      <li>
        <button
          onClick={() => onSelect(node.slug)}
          className={cn(
            "group flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm transition-all",
            "hover:bg-[var(--surface-high)]",
            isActive && "bg-primary/10 text-primary font-medium border-l-2 border-primary -ml-[2px]",
            !isActive && "text-foreground"
          )}
          style={{ paddingLeft: `${12 + depth * 16}px` }}
        >
          {/* Expand/collapse for parents */}
          {hasChildren ? (
            <span
              onClick={(e) => {
                e.stopPropagation();
                toggleExpand(node.slug);
              }}
              className="shrink-0 cursor-pointer text-muted-foreground hover:text-foreground"
            >
              {isExpanded ? (
                <ChevronDown className="h-3.5 w-3.5" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5" />
              )}
            </span>
          ) : (
            <span className="w-3.5 shrink-0" />
          )}

          <StatusDot status={node.status} />
          <span className="flex-1 truncate text-left">{node.title}</span>
          <span className="text-xs text-muted-foreground tabular-nums opacity-60 group-hover:opacity-100">
            {node.word_count}w
          </span>
        </button>
      </li>
      {hasChildren && isExpanded && (
        node.children.map((child) => (
          <SectionTreeItem
            key={child.slug}
            node={child}
            depth={depth + 1}
            activeSlug={activeSlug}
            onSelect={onSelect}
            expandedSlugs={expandedSlugs}
            toggleExpand={toggleExpand}
          />
        ))
      )}
    </>
  );
}

export function SectionSidebar({
  sections,
  activeSlug,
  onSelect,
  projectName,
  projectVersion,
  projectSlug,
  onNavigateSettings,
}: SectionSidebarProps) {
  const tree = useMemo(() => buildTree(sections), [sections]);

  // Start with all parent nodes expanded
  const [expandedSlugs, setExpandedSlugs] = useState<Set<string>>(() => {
    const parents = new Set<string>();
    for (const s of sections) {
      if (s.parent_slug) parents.add(s.parent_slug);
    }
    return parents;
  });

  const toggleExpand = (slug: string) => {
    setExpandedSlugs((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  };

  return (
    <nav className="w-60 shrink-0 border-r bg-[var(--surface-dim)] flex flex-col overflow-hidden">
      {/* Project header */}
      {projectName && (
        <div className="px-4 py-3 border-b">
          <h3 className="text-sm font-semibold truncate">{projectName}</h3>
          {projectVersion && (
            <span className="text-xs text-muted-foreground">v{projectVersion}.0</span>
          )}
        </div>
      )}

      {/* Section list */}
      <div className="flex-1 overflow-y-auto no-scrollbar">
        <ul className="space-y-0.5 p-2">
          {tree.map((node) => (
            <SectionTreeItem
              key={node.slug}
              node={node}
              depth={0}
              activeSlug={activeSlug}
              onSelect={onSelect}
              expandedSlugs={expandedSlugs}
              toggleExpand={toggleExpand}
            />
          ))}
        </ul>
      </div>

      {/* Bottom pinned section */}
      <div className="border-t p-3 space-y-2">
        <Button
          variant="default"
          size="sm"
          className="w-full justify-center gap-1.5"
          onClick={() => {
            /* New section — will be wired later */
          }}
        >
          <Plus className="h-3.5 w-3.5" />
          New Section
        </Button>

        <div className="space-y-0.5">
          {onNavigateSettings && (
            <button
              onClick={onNavigateSettings}
              className="flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-[var(--surface-high)] transition-colors"
            >
              <Settings className="h-3.5 w-3.5" />
              Settings
            </button>
          )}
          <button className="ui-placeholder flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-xs text-muted-foreground">
            <BookOpen className="h-3.5 w-3.5" />
            Documentation
          </button>
          <button className="ui-placeholder flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-xs text-muted-foreground">
            <Archive className="h-3.5 w-3.5" />
            Archive
          </button>
        </div>
      </div>
    </nav>
  );
}
