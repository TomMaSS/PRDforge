"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { TokenStats } from "@/lib/types";
import { Zap, TrendingDown, Activity, BarChart3 } from "lucide-react";

interface TokenStatsDashboardProps {
  stats: TokenStats;
}

export function TokenStatsDashboard({ stats }: TokenStatsDashboardProps) {
  return (
    <div className="space-y-6">
      {/* Explainer */}
      <div className="rounded-lg border bg-muted/50 p-4">
        <h3 className="text-sm font-semibold mb-1">
          What are token savings?
        </h3>
        <p className="text-sm text-muted-foreground">
          PRDforge uses smart context management to reduce the number of
          tokens sent to the LLM on each operation. Token savings represent
          the difference between sending the full document versus the
          optimized context window.
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Total Operations
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.total_operations.toLocaleString()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Tokens Saved
            </CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.total_tokens_saved.toLocaleString()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Savings Rate
            </CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.savings_percentage.toFixed(1)}%
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Avg Tokens/Section
            </CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.project_stats.avg_tokens_per_section.toLocaleString()}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Per-operation breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">By Operation</CardTitle>
          <CardDescription>
            Token savings breakdown per operation type
          </CardDescription>
        </CardHeader>
        <CardContent>
          {stats.by_operation.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No operations recorded yet.
            </p>
          ) : (
            <div className="space-y-3">
              {stats.by_operation.map((op) => (
                <div
                  key={op.operation}
                  className="flex items-center justify-between"
                >
                  <div>
                    <span className="text-sm font-medium">
                      {op.operation}
                    </span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {op.count} calls
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm tabular-nums">
                      {op.tokens_saved.toLocaleString()} saved
                    </span>
                    <Badge variant="secondary" className="text-xs">
                      avg {op.avg_savings.toLocaleString()}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent activity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {stats.activity.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No recent activity.
            </p>
          ) : (
            <div className="space-y-2">
              {stats.activity.map((item, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between text-sm"
                >
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {item.operation}
                    </Badge>
                    <span className="text-muted-foreground">
                      {item.section}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <span className="tabular-nums">
                      {item.tokens_saved.toLocaleString()} saved
                    </span>
                    <span className="text-xs">
                      {new Date(item.timestamp).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
