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
      <div className="rounded-lg border bg-muted/50 p-4">
        <h3 className="text-sm font-semibold mb-1">What are token savings?</h3>
        <p className="text-sm text-muted-foreground">
          PRDforge loads only the sections you need plus summaries of dependencies,
          instead of the full document. Token savings show how much context was avoided.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Operations</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.operations.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Tokens Saved</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_saved_tokens.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Savings Rate</CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.savings_percent.toFixed(1)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Sections</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.project_stats.sections}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">By Operation</CardTitle>
          <CardDescription>Token savings per operation type</CardDescription>
        </CardHeader>
        <CardContent>
          {stats.by_operation.length === 0 ? (
            <p className="text-sm text-muted-foreground">No operations recorded yet.</p>
          ) : (
            <div className="space-y-3">
              {stats.by_operation.map((op) => {
                const saved = op.full_tokens - op.loaded_tokens;
                return (
                  <div key={op.operation} className="flex items-center justify-between">
                    <div>
                      <span className="text-sm font-medium">{op.operation}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{op.count} calls</span>
                    </div>
                    <span className="text-sm tabular-nums">{saved.toLocaleString()} saved</span>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Write Operations</CardTitle>
        </CardHeader>
        <CardContent>
          {stats.activity.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent activity.</p>
          ) : (
            <div className="space-y-2">
              {stats.activity.slice(0, 20).map((item, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <Badge variant="outline" className="text-xs">
                    {item.tool_name}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
