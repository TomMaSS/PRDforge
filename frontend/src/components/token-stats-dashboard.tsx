"use client";

import { useMemo } from "react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { Wrench } from "lucide-react";
import type { TokenStats } from "@/lib/types";

interface TokenStatsDashboardProps {
  stats: TokenStats;
}

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toString();
}

function StatCard({ label, value, subtitle, color }: {
  label: string; value: string; subtitle?: string; color: string;
}) {
  return (
    <div className="rounded-lg p-4" style={{ background: "var(--card-bg)", border: "1px solid var(--border-color)" }}>
      <div className="text-xs font-medium text-muted-foreground mb-1">{label}</div>
      <div className="text-2xl font-bold tabular-nums" style={{ color }}>{value}</div>
      {subtitle && <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>}
    </div>
  );
}

function GaugeRing({ percent, size = 100, label = "saved" }: { percent: number; size?: number; label?: string }) {
  const r = (size - 12) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - percent / 100);
  const color = percent > 80 ? "#22c55e" : percent > 50 ? "#f59e0b" : "#ef4444";

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--surface)" strokeWidth={8} />
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke={color} strokeWidth={8} strokeLinecap="round"
        strokeDasharray={circumference} strokeDashoffset={offset}
        transform={`rotate(-90 ${size/2} ${size/2})`}
      />
      <text x={size/2} y={size/2 - 6} textAnchor="middle" fill="var(--fg)" fontSize={20} fontWeight={700} fontFamily="Inter">
        {percent.toFixed(1)}%
      </text>
      <text x={size/2} y={size/2 + 12} textAnchor="middle" fill="var(--fg-muted)" fontSize={10} fontFamily="Inter">
        {label}
      </text>
    </svg>
  );
}

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#38bdf8", "#a855f7"];

const tooltipStyle = {
  contentStyle: {
    background: "var(--card-bg)",
    border: "1px solid var(--border-color)",
    borderRadius: 8,
    fontSize: 12,
    color: "var(--fg)",
  },
  labelStyle: { color: "var(--fg-muted)" },
};

export function TokenStatsDashboard({ stats }: TokenStatsDashboardProps) {
  const dailyData = useMemo(() =>
    stats.daily_trend.map((d) => ({
      day: d.day.slice(5), // MM-DD
      saved: d.tokens_saved,
      ops: d.operations,
    })),
  [stats.daily_trend]);

  const comparisonData = useMemo(() => [
    { name: "Full Doc", tokens: stats.total_full_doc_tokens, fill: "#ef4444" },
    { name: "Loaded", tokens: stats.total_loaded_tokens, fill: "#22c55e" },
  ], [stats]);

  const opData = useMemo(() =>
    stats.by_operation.map((op, i) => ({
      name: op.operation.replace(/_/g, " "),
      saved: op.full_tokens - op.loaded_tokens,
      loaded: op.loaded_tokens,
      count: op.count,
      fill: COLORS[i % COLORS.length],
    })),
  [stats.by_operation]);

  const activityByTool = useMemo(() => {
    const map = new Map<string, number>();
    for (const a of stats.activity) {
      const name = a.tool_name.replace(/^prd_/, "");
      map.set(name, (map.get(name) || 0) + 1);
    }
    return Array.from(map.entries())
      .map(([name, count], i) => ({ name, count, fill: COLORS[i % COLORS.length] }))
      .sort((a, b) => b.count - a.count);
  }, [stats.activity]);

  return (
    <div className="space-y-5">
      {/* Top stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="rounded-lg p-4 flex items-center justify-center" style={{ background: "var(--card-bg)", border: "1px solid var(--border-color)" }}>
          <GaugeRing percent={stats.savings_percent} size={90} label="avg / session" />
        </div>
        <StatCard label="Sessions" value={stats.sessions > 0 ? stats.sessions.toString() : stats.operations.toLocaleString()} subtitle={stats.sessions > 0 ? `${stats.avg_sections_per_session.toFixed(1)} sections/session` : "operations total"} color="#6366f1" />
        <StatCard label="Best Session" value={`${stats.best_session_savings.toFixed(1)}%`} subtitle="highest savings" color="#22c55e" />
        <StatCard label="Full Document" value={formatNum(stats.total_full_doc_tokens)} subtitle={`${stats.project_stats.sections} sections`} color="#38bdf8" />
        <StatCard label="Project" value={stats.project_stats.dependencies.toString()} subtitle={`deps · ${stats.project_stats.revisions} revisions`} color="#a855f7" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* 7-Day Trend — Area Chart */}
        <div className="rounded-lg p-4" style={{ background: "var(--card-bg)", border: "1px solid var(--border-color)" }}>
          <div className="text-xs font-medium text-muted-foreground mb-3">7-Day Token Savings</div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={dailyData}>
              <defs>
                <linearGradient id="gradSaved" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22c55e" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis dataKey="day" tick={{ fontSize: 10, fill: "var(--fg-muted)" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "var(--fg-muted)" }} axisLine={false} tickLine={false} tickFormatter={formatNum} />
              <Tooltip {...tooltipStyle} formatter={(v) => [formatNum(Number(v)), "Tokens Saved"]} />
              <Area type="monotone" dataKey="saved" stroke="#22c55e" strokeWidth={2} fill="url(#gradSaved)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Token Comparison — Bar Chart */}
        <div className="rounded-lg p-4" style={{ background: "var(--card-bg)", border: "1px solid var(--border-color)" }}>
          <div className="text-xs font-medium text-muted-foreground mb-3">Full Doc vs Loaded</div>
          <div className="flex items-end gap-6 justify-center h-[200px]">
            {comparisonData.map((d) => {
              const maxH = 160;
              const h = Math.max(8, (d.tokens / stats.total_full_doc_tokens) * maxH);
              return (
                <div key={d.name} className="flex flex-col items-center gap-2">
                  <span className="text-lg font-bold tabular-nums" style={{ color: d.fill }}>{formatNum(d.tokens)}</span>
                  <div
                    className="w-16 rounded-t-md transition-all"
                    style={{ height: h, background: d.fill, opacity: 0.8 }}
                  />
                  <span className="text-xs text-muted-foreground">{d.name}</span>
                </div>
              );
            })}
            <div className="flex flex-col items-center gap-2">
              <span className="text-lg font-bold tabular-nums text-muted-foreground">{formatNum(stats.total_saved_tokens)}</span>
              <div
                className="w-16 rounded-t-md border-2 border-dashed"
                style={{ height: Math.max(8, (stats.total_saved_tokens / stats.total_full_doc_tokens) * 160), borderColor: "#6366f1", opacity: 0.5 }}
              />
              <span className="text-xs text-muted-foreground">Saved</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* By Operation — Horizontal Bars */}
        <div className="lg:col-span-2 rounded-lg p-4" style={{ background: "var(--card-bg)", border: "1px solid var(--border-color)" }}>
          <div className="text-xs font-medium text-muted-foreground mb-3">Savings by Operation</div>
          {opData.length === 0 ? (
            <p className="text-sm text-muted-foreground">No operations yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(120, opData.length * 50)}>
              <BarChart data={opData} layout="vertical" margin={{ left: 10, right: 20, top: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: "var(--fg-muted)" }} axisLine={false} tickLine={false} tickFormatter={formatNum} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "var(--fg)" }} width={110} axisLine={false} tickLine={false} />
                <Tooltip {...tooltipStyle} formatter={(v, name) => [formatNum(Number(v)), name === "saved" ? "Tokens Saved" : "Tokens Loaded"]} />
                <Bar dataKey="saved" radius={[0, 4, 4, 0]} barSize={18}>
                  {opData.map((d, i) => <Cell key={i} fill={d.fill} opacity={0.85} />)}
                </Bar>
                <Bar dataKey="loaded" fill="var(--surface)" radius={[0, 4, 4, 0]} barSize={18} opacity={0.4} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Activity Breakdown — Donut */}
        <div className="rounded-lg p-4" style={{ background: "var(--card-bg)", border: "1px solid var(--border-color)" }}>
          <div className="text-xs font-medium text-muted-foreground mb-3">Write Operations ({stats.activity.length})</div>
          {activityByTool.length === 0 ? (
            <p className="text-sm text-muted-foreground">No activity yet.</p>
          ) : (
            <div className="flex flex-col items-center">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie
                    data={activityByTool} dataKey="count" nameKey="name"
                    cx="50%" cy="50%" innerRadius={40} outerRadius={70}
                    paddingAngle={2} strokeWidth={0}
                  >
                    {activityByTool.map((d, i) => <Cell key={i} fill={d.fill} />)}
                  </Pie>
                  <Tooltip {...tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2">
                {activityByTool.map((d) => (
                  <div key={d.name} className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full shrink-0" style={{ background: d.fill }} />
                    <span className="text-xs text-muted-foreground truncate">{d.name}</span>
                    <span className="text-xs tabular-nums ml-auto">{d.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Section Heatmap */}
      {stats.section_heatmap && stats.section_heatmap.length > 0 && (
        <div className="rounded-lg p-4" style={{ background: "var(--card-bg)", border: "1px solid var(--border-color)" }}>
          <div className="text-xs font-medium text-muted-foreground mb-3">Section Access Heatmap</div>
          <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2">
            {stats.section_heatmap.map((s) => {
              const maxCount = Math.max(...stats.section_heatmap.map((h) => h.access_count));
              const intensity = maxCount > 0 ? s.access_count / maxCount : 0;
              const bg = s.has_full_read
                ? `rgba(99, 102, 241, ${0.15 + intensity * 0.6})`
                : `rgba(148, 150, 173, ${0.1 + intensity * 0.3})`;
              return (
                <div
                  key={s.slug}
                  className="rounded-md p-2.5 text-center"
                  style={{ background: bg, border: "1px solid var(--border-color)" }}
                  title={`${s.title}: ${s.access_count} accesses`}
                >
                  <div className="text-xs font-medium truncate" style={{ color: "var(--fg)" }}>
                    {s.title.length > 14 ? s.title.slice(0, 13) + "…" : s.title}
                  </div>
                  <div className="text-lg font-bold tabular-nums mt-0.5" style={{ color: s.has_full_read ? "#6366f1" : "var(--fg-muted)" }}>
                    {s.access_count}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Recent Activity Timeline */}
      <div className="rounded-lg p-4" style={{ background: "var(--card-bg)", border: "1px solid var(--border-color)" }}>
        <div className="text-xs font-medium text-muted-foreground mb-3">Recent Activity</div>
        <div className="space-y-1.5 max-h-48 overflow-y-auto">
          {stats.activity.slice(0, 15).map((item, i) => {
            const detail = typeof item.detail === "string" ? JSON.parse(item.detail) : item.detail;
            const slug = detail?.slug || detail?.from || detail?.to || "";
            return (
              <div key={i} className="flex items-center gap-3 py-1.5 text-xs border-b border-border/30 last:border-0">
                <Wrench className="h-3 w-3 text-muted-foreground shrink-0" />
                <span className="font-medium text-foreground">{item.tool_name.replace(/^prd_/, "")}</span>
                {slug && <span className="text-muted-foreground">{slug}</span>}
                <span className="ml-auto text-muted-foreground tabular-nums whitespace-nowrap">
                  {new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
