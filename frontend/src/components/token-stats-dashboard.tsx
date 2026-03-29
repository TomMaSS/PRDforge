"use client";

import { useMemo, useState, useEffect } from "react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { Wrench, AlertTriangle, RefreshCw, Activity } from "lucide-react";
import type { TokenStats } from "@/lib/types";

interface TokenStatsDashboardProps {
  stats: TokenStats;
  projectSlug?: string;
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
    fontSize: 13,
    color: "var(--fg)",
    boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
    padding: "10px 14px",
  },
  labelStyle: {
    color: "var(--fg)",
    fontWeight: 600,
    marginBottom: 4,
  },
  itemStyle: {
    color: "var(--fg)",
    padding: "2px 0",
  },
};

function StatsContent({ stats }: { stats: TokenStats }) {
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
            {(() => {
              const maxH = 160;
              const maxTokens = Math.max(stats.total_full_doc_tokens, stats.total_loaded_tokens, stats.total_saved_tokens, 1);
              return (
                <>
                  {comparisonData.map((d) => {
                    const h = Math.max(8, Math.min(maxH, (d.tokens / maxTokens) * maxH));
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
                      style={{ height: Math.max(8, Math.min(maxH, (stats.total_saved_tokens / maxTokens) * maxH)), borderColor: "#6366f1", opacity: 0.5 }}
                    />
                    <span className="text-xs text-muted-foreground">Saved</span>
                  </div>
                </>
              );
            })()}
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

/* ============================================
   Log View sub-tab
   ============================================ */
function LogViewContent({ projectSlug }: { projectSlug?: string }) {
  const [auditLog, setAuditLog] = useState<Array<{
    action: string;
    resource: string;
    detail: Record<string, unknown>;
    user_id: string | null;
    created_at: string;
  }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectSlug) return;
    fetch(`/api/projects/${projectSlug}/audit`)
      .then((r) => r.ok ? r.json() : [])
      .then((data) => setAuditLog(Array.isArray(data) ? data : []))
      .catch(() => setAuditLog([]))
      .finally(() => setLoading(false));
  }, [projectSlug]);

  if (loading) {
    return <div className="text-sm text-muted-foreground text-center py-12">Loading audit log...</div>;
  }

  return (
    <div className="space-y-5">
      {/* Filters — non-functional placeholders */}
      <div className="flex items-center gap-3">
        <select className="ui-placeholder input-etched rounded-lg px-3 py-2 text-sm" disabled>
          <option>All Contributors</option>
        </select>
        <select className="ui-placeholder input-etched rounded-lg px-3 py-2 text-sm" disabled>
          <option>Any Action</option>
        </select>
        <button className="ui-placeholder ml-auto flex items-center gap-1.5 rounded-lg border border-[var(--accent)] px-3 py-2 text-xs font-semibold text-[var(--accent)]" disabled>
          <RefreshCw className="h-3.5 w-3.5" />
          Live Refresh
        </button>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-[var(--border-color)] bg-[var(--card-bg)] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border-color)] bg-[var(--surface-dim)]">
              <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Timestamp</th>
              <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Action</th>
              <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Resource</th>
              <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Detail</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-color)]">
            {auditLog.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">No activity recorded</td></tr>
            ) : (
              auditLog.slice(0, 25).map((entry, i) => (
                <tr key={i} className="hover:bg-[var(--surface)]/30 transition-colors">
                  <td className="px-4 py-3 text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                    {new Date(entry.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-xs font-medium">{entry.action}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{entry.resource}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground max-w-[200px] truncate">
                    {JSON.stringify(entry.detail).slice(0, 60)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ============================================
   Alerts sub-tab (non-functional placeholder)
   ============================================ */
function AlertsContent() {
  return (
    <div className="space-y-5">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="ui-placeholder rounded-xl border border-[var(--border-color)] bg-[var(--card-bg)] p-5 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <AlertTriangle className="h-5 w-5 text-[var(--status-error)]" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Critical</span>
          </div>
          <div className="text-3xl font-bold tabular-nums">0</div>
        </div>
        <div className="ui-placeholder rounded-xl border border-[var(--border-color)] bg-[var(--card-bg)] p-5 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Activity className="h-5 w-5 text-[var(--status-warning)]" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Review</span>
          </div>
          <div className="text-3xl font-bold tabular-nums">0</div>
        </div>
        <div className="ui-placeholder rounded-xl border border-[var(--border-color)] bg-[var(--card-bg)] p-5 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Activity className="h-5 w-5 text-[var(--accent)]" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Suggestions</span>
          </div>
          <div className="text-3xl font-bold tabular-nums">0</div>
        </div>
      </div>

      {/* Empty alert list */}
      <div className="rounded-xl border border-[var(--border-color)] bg-[var(--card-bg)] p-8 text-center">
        <AlertTriangle className="h-8 w-8 text-muted-foreground mx-auto mb-3 opacity-40" />
        <p className="text-sm text-muted-foreground">No alerts</p>
        <p className="text-xs text-muted-foreground mt-1">
          Dependency conflicts, outdated sections, and AI suggestions will appear here.
        </p>
      </div>
    </div>
  );
}

/* ============================================
   Main wrapper with sub-tabs
   ============================================ */
const SUB_TABS = [
  { value: "stats", label: "Stats" },
  { value: "log-view", label: "Log View" },
  { value: "alerts", label: "Alerts" },
] as const;

export function TokenStatsDashboard({ stats, projectSlug }: TokenStatsDashboardProps) {
  const [subTab, setSubTab] = useState<string>("stats");

  return (
    <div className="space-y-5">
      {/* Sub-tab bar */}
      <div className="flex items-center gap-1 border-b border-[var(--border-color)] pb-0">
        {SUB_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setSubTab(tab.value)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
              subTab === tab.value
                ? "border-[var(--accent)] text-[var(--accent)]"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sub-tab content */}
      {subTab === "stats" && <StatsContent stats={stats} />}
      {subTab === "log-view" && <LogViewContent projectSlug={projectSlug} />}
      {subTab === "alerts" && <AlertsContent />}
    </div>
  );
}
