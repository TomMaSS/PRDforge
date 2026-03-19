"use client";

import Link from "next/link";
import { ChevronRight, Moon, Sun, User } from "lucide-react";
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

interface TopBarProps {
  projectName?: string;
  projectSlug?: string;
  sectionTitle?: string;
}

export function TopBar({ projectName, projectSlug, sectionTitle }: TopBarProps) {
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
      <Link href="/projects" className="text-lg font-bold tracking-tight">
        PRDforge
      </Link>

      {projectName && (
        <nav className="flex items-center gap-1 text-sm text-muted-foreground">
          <ChevronRight className="h-4 w-4" />
          <span className={cn(sectionTitle ? "" : "text-foreground font-medium")}>
            {projectName}
          </span>
          {sectionTitle && (
            <>
              <ChevronRight className="h-4 w-4" />
              <span className="text-foreground font-medium">
                {sectionTitle}
              </span>
            </>
          )}
        </nav>
      )}

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
              <DropdownMenuItem onClick={() => router.push(`/projects/${projectSlug}/settings`)}>
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
