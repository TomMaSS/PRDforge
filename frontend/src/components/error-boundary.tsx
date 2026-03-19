"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorBoundaryFallbackProps {
  error: Error;
  onRetry: () => void;
}

export function ErrorBoundaryFallback({
  error,
  onRetry,
}: ErrorBoundaryFallbackProps) {
  return (
    <div className="flex min-h-[200px] items-center justify-center">
      <div className="text-center space-y-3">
        <AlertTriangle className="mx-auto h-8 w-8 text-destructive" />
        <p className="text-sm font-medium">Something went wrong</p>
        <p className="text-xs text-muted-foreground max-w-sm">
          {error.message}
        </p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RefreshCw className="mr-1.5 h-3 w-3" />
          Retry
        </Button>
      </div>
    </div>
  );
}

interface APIDownBannerProps {
  onRetry: () => void;
  retryIn?: number;
}

export function APIDownBanner({ onRetry, retryIn }: APIDownBannerProps) {
  return (
    <div className="border-b bg-amber-50 dark:bg-amber-950 px-4 py-2 flex items-center justify-between text-sm">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-600" />
        <span>
          Unable to reach the server. Your unsaved changes are preserved.
        </span>
      </div>
      <div className="flex items-center gap-2">
        {retryIn !== undefined && (
          <span className="text-xs text-muted-foreground">
            Retrying in {retryIn}s...
          </span>
        )}
        <Button variant="outline" size="sm" onClick={onRetry}>
          Retry Now
        </Button>
      </div>
    </div>
  );
}

interface SessionExpiredDialogProps {
  onSignIn: () => void;
}

export function SessionExpiredDialog({ onSignIn }: SessionExpiredDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="rounded-lg border bg-card p-6 shadow-lg max-w-sm w-full text-center space-y-4">
        <div className="mx-auto h-10 w-10 rounded-full bg-muted flex items-center justify-center">
          <AlertTriangle className="h-5 w-5" />
        </div>
        <div>
          <h3 className="font-semibold">Session expired</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Your session has ended. Sign in again to continue. Your work is
            saved.
          </p>
        </div>
        <Button onClick={onSignIn} className="w-full">
          Sign In Again
        </Button>
      </div>
    </div>
  );
}

interface ConflictDialogProps {
  theirVersion: string;
  myVersion: string;
  updatedBy: string;
  onDiscard: () => void;
  onOverwrite: () => void;
  onCopyMine: () => void;
}

export function ConflictDialog({
  theirVersion,
  myVersion,
  updatedBy,
  onDiscard,
  onOverwrite,
  onCopyMine,
}: ConflictDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="rounded-lg border bg-card p-6 shadow-lg max-w-lg w-full space-y-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-500" />
          <h3 className="font-semibold">Edit conflict</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          {updatedBy} updated this section while you were editing. Your changes
          haven&apos;t been saved.
        </p>
        <div className="space-y-2">
          <div className="rounded border p-3">
            <p className="text-xs font-medium text-muted-foreground mb-1">
              Their version (current):
            </p>
            <p className="text-sm line-clamp-3">{theirVersion}</p>
          </div>
          <div className="rounded border p-3">
            <p className="text-xs font-medium text-muted-foreground mb-1">
              Your version (unsaved):
            </p>
            <p className="text-sm line-clamp-3">{myVersion}</p>
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="outline" size="sm" onClick={onDiscard}>
            Discard My Changes
          </Button>
          <Button variant="destructive" size="sm" onClick={onOverwrite}>
            Overwrite
          </Button>
          <Button variant="secondary" size="sm" onClick={onCopyMine}>
            Copy Mine
          </Button>
        </div>
      </div>
    </div>
  );
}
