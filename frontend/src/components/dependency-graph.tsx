import { cn } from "@/lib/utils";
import { GitBranch } from "lucide-react";

interface DependencyGraphProps {
  className?: string;
}

export function DependencyGraph({ className }: DependencyGraphProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed p-12 text-center",
        className
      )}
    >
      <GitBranch className="h-10 w-10 text-muted-foreground/50 mb-3" />
      <h3 className="text-sm font-semibold">Dependency Graph</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        Visual dependency mapping will be available in a future release.
      </p>
    </div>
  );
}
