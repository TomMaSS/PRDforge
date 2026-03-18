"use client";

import { useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  FolderOpen,
  Plus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusDot } from "@/components/status-dot";
import { cn } from "@/lib/utils";
import type { Project, Section } from "@/lib/types";

interface SidebarProps {
  projects: Project[];
  sections: Section[];
  activeProject?: string;
  activeSection?: string;
  onProjectSelect: (slug: string) => void;
  onSectionSelect: (slug: string) => void;
  onCreateProject?: () => void;
  onCreateSection?: () => void;
}

export function Sidebar({
  projects,
  sections,
  activeProject,
  activeSection,
  onProjectSelect,
  onSectionSelect,
  onCreateProject,
  onCreateSection,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <aside className="flex w-10 flex-col items-center border-r bg-muted/30 py-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCollapsed(false)}
          aria-label="Expand sidebar"
          className="h-8 w-8"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </aside>
    );
  }

  return (
    <aside className="flex w-64 flex-col border-r bg-muted/30">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <span className="text-sm font-semibold">Projects</span>
        <div className="flex items-center gap-1">
          {onCreateProject && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onCreateProject}
              aria-label="Create project"
              className="h-7 w-7"
            >
              <Plus className="h-4 w-4" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed(true)}
            aria-label="Collapse sidebar"
            className="h-7 w-7"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <nav className="space-y-0.5 px-2 py-2">
          {projects.map((project) => (
            <button
              key={project.slug}
              onClick={() => onProjectSelect(project.slug)}
              className={cn(
                "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent",
                activeProject === project.slug &&
                  "bg-accent text-accent-foreground font-medium"
              )}
            >
              <FolderOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate">{project.name}</span>
            </button>
          ))}
        </nav>

        {activeProject && sections.length > 0 && (
          <>
            <div className="flex items-center justify-between px-4 py-2 border-t">
              <span className="text-xs font-semibold uppercase text-muted-foreground">
                Sections
              </span>
              {onCreateSection && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onCreateSection}
                  aria-label="Create section"
                  className="h-6 w-6"
                >
                  <Plus className="h-3 w-3" />
                </Button>
              )}
            </div>
            <nav className="space-y-0.5 px-2 pb-2">
              {sections.map((section) => (
                <button
                  key={section.slug}
                  onClick={() => onSectionSelect(section.slug)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent",
                    activeSection === section.slug &&
                      "bg-accent text-accent-foreground font-medium"
                  )}
                >
                  <StatusDot status={section.status} />
                  <span className="truncate">{section.title}</span>
                </button>
              ))}
            </nav>
          </>
        )}
      </div>
    </aside>
  );
}
