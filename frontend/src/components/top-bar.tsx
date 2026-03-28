"use client";

import Link from "next/link";
import {
  ArrowLeft,
  Moon,
  Sun,
  User,
  FileText,
  MessageSquare,
  GitBranch,
  Clock,
  BarChart3,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { signOut } from "@/lib/auth-client";

const PROJECT_TABS = [
  { value: "sections", label: "Sections", icon: FileText },
  { value: "comments", label: "Comments", icon: MessageSquare },
  { value: "dependencies", label: "Dependencies", icon: GitBranch },
  { value: "changelog", label: "Changelog", icon: Clock },
  { value: "stats", label: "Stats", icon: BarChart3 },
] as const;

interface TopBarProps {
  variant: "dashboard" | "project" | "settings";
  activeTab?: string;
  onTabChange?: (tab: string) => void;
  projectName?: string;
  projectSlug?: string;
  onBack?: () => void;
}

export function TopBar({
  variant,
  activeTab,
  onTabChange,
  projectName,
  projectSlug,
  onBack,
}: TopBarProps) {
  const router = useRouter();
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
  }, []);

  const toggleTheme = useCallback(() => {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("prdforge-theme", next ? "dark" : "light");
  }, [isDark]);

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-4 border-b bg-card px-6">
      {/* Logo */}
      <Link href="/projects" className="text-lg font-bold tracking-tight shrink-0">
        PRDforge
      </Link>

      {/* Variant: settings — back arrow */}
      {variant === "settings" && (
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="hidden sm:inline">{projectName || "Back"}</span>
        </button>
      )}

      {/* Variant: project — inline tabs */}
      {variant === "project" && (
        <nav className="flex items-center gap-1 ml-2" role="tablist">
          {PROJECT_TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.value;
            return (
              <button
                key={tab.value}
                role="tab"
                aria-selected={isActive}
                onClick={() => onTabChange?.(tab.value)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                <span className="hidden md:inline">{tab.label}</span>
              </button>
            );
          })}
        </nav>
      )}

      {/* Right actions */}
      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label="Toggle theme"
        >
          {isDark ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="User menu">
              <User className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {projectSlug && (
              <DropdownMenuItem
                onClick={() =>
                  router.push(`/projects/${projectSlug}/settings`)
                }
              >
                Settings
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={async () => {
                await signOut();
                router.push("/signin");
              }}
            >
              Sign Out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
