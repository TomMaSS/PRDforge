"use client";

import { StatusDot } from "@/components/status-dot";
import { cn } from "@/lib/utils";
import type { SectionListItem } from "@/lib/types";

interface SectionSidebarProps {
  sections: SectionListItem[];
  activeSlug?: string;
  onSelect: (slug: string) => void;
}

export function SectionSidebar({
  sections,
  activeSlug,
  onSelect,
}: SectionSidebarProps) {
  return (
    <nav className="w-56 shrink-0 border-r overflow-y-auto">
      <div className="px-4 py-3 border-b">
        <h3 className="text-sm font-semibold">Sections</h3>
      </div>
      <ul className="space-y-0.5 p-2">
        {sections.map((section) => (
          <li key={section.slug}>
            <button
              onClick={() => onSelect(section.slug)}
              className={cn(
                "flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors hover:bg-accent",
                activeSlug === section.slug &&
                  "bg-accent text-accent-foreground font-medium"
              )}
            >
              <StatusDot status={section.status} />
              <span className="flex-1 truncate text-left">
                {section.title}
              </span>
              <span className="text-xs text-muted-foreground tabular-nums">
                {section.word_count}w
              </span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
