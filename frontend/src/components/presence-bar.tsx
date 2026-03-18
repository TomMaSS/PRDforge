"use client";

import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface PresenceUser {
  id: string;
  name: string;
  activeSection?: string;
}

interface PresenceBarProps {
  users: PresenceUser[];
  connected: boolean;
  className?: string;
}

const AVATAR_COLORS = [
  "bg-blue-500",
  "bg-green-500",
  "bg-purple-500",
  "bg-amber-500",
  "bg-pink-500",
  "bg-cyan-500",
  "bg-red-500",
  "bg-indigo-500",
];

function getColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) | 0;
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function PresenceBar({ users, connected, className }: PresenceBarProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className={cn(
          "h-2 w-2 rounded-full",
          connected ? "bg-green-500" : "bg-amber-500"
        )}
      />
      <span className="text-xs text-muted-foreground">
        {connected ? "Live" : "Reconnecting..."}
      </span>

      {users.length > 0 && (
        <TooltipProvider>
          <div className="flex -space-x-2">
            {users.slice(0, 8).map((user) => (
              <Tooltip key={user.id}>
                <TooltipTrigger asChild>
                  <div
                    className={cn(
                      "flex h-7 w-7 items-center justify-center rounded-full border-2 border-background text-xs font-medium text-white",
                      getColor(user.id)
                    )}
                  >
                    {getInitials(user.name)}
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{user.name}</p>
                  {user.activeSection && (
                    <p className="text-xs text-muted-foreground">
                      Viewing: {user.activeSection}
                    </p>
                  )}
                </TooltipContent>
              </Tooltip>
            ))}
            {users.length > 8 && (
              <div className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-background bg-muted text-xs">
                +{users.length - 8}
              </div>
            )}
          </div>
        </TooltipProvider>
      )}
    </div>
  );
}
