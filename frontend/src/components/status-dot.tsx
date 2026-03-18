import { cn } from "@/lib/utils";
import type { SectionStatus } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-400",
  in_progress: "bg-blue-500",
  review: "bg-amber-500",
  approved: "bg-green-500",
  outdated: "bg-red-500",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  in_progress: "In Progress",
  review: "Review",
  approved: "Approved",
  outdated: "Outdated",
};

interface StatusDotProps {
  status: SectionStatus;
  showLabel?: boolean;
  className?: string;
}

export function StatusDot({ status, showLabel = false, className }: StatusDotProps) {
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <span
        className={cn(
          "inline-block h-2 w-2 rounded-full",
          STATUS_COLORS[status] ?? "bg-gray-400"
        )}
        aria-label={STATUS_LABELS[status] ?? status}
      />
      {showLabel && (
        <span className="text-xs text-muted-foreground">
          {STATUS_LABELS[status] ?? status}
        </span>
      )}
    </span>
  );
}
