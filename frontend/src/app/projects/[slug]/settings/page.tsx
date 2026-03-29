"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Check,
  CheckCircle2,
  XCircle,
  ExternalLink,
  ChevronRight,
  Settings,
  User,
  Key,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { TopBar } from "@/components/top-bar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
// Card components no longer used — Stitch uses raw sections
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LoadingOverlay } from "@/components/loading-overlay";
import { MemberManager } from "@/components/member-manager";

const PROVIDERS = ["claude_cli", "anthropic_api"] as const;
const MODELS = ["sonnet", "opus", "haiku"] as const;

const ORG_SLUG = "default";

interface Member {
  id: string;
  user_id: string;
  role: string;
  name?: string;
  email?: string;
  created_at: string;
}

interface Settings {
  claude_comment_replies: boolean;
  chat_enabled: boolean;
  chat_provider: string;
  chat_model: string;
}

interface ProviderStatus {
  claude_cli: { installed: boolean; logged_in: boolean };
  anthropic_api: { configured: boolean; key_hint: string };
}

export default function SettingsPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const slug = params.slug;

  const [settings, setSettings] = useState<Settings | null>(null);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [savingKey, setSavingKey] = useState(false);
  const [loggingIn, setLoggingIn] = useState(false);
  const [showCodeInput, setShowCodeInput] = useState(false);
  const [loginCode, setLoginCode] = useState("");
  const [members, setMembers] = useState<Member[]>([]);

  useEffect(() => {
    Promise.all([
      fetch(`/api/projects/${slug}/settings`).then((r) => r.json()),
      fetch("/api/chat/provider-status").then((r) => r.json()),
      fetch(`/api/projects/${slug}/members`).then((r) => r.ok ? r.json() : []),
    ])
      .then(([s, p, m]) => {
        setSettings(s);
        setProviderStatus(p);
        setMembers(m);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [slug]);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const res = await fetch(`/api/projects/${slug}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (!res.ok) {
        const data = await res.json();
        toast.error(data.error || "Failed to save");
        return;
      }
      const updated = await res.json();
      setSettings(updated);
      toast.success("Settings saved");
    } catch {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const update = (patch: Partial<Settings>) => {
    setSettings((prev) => (prev ? { ...prev, ...patch } : prev));
  };

  const handleCliLogin = async () => {
    setLoggingIn(true);
    try {
      const res = await fetch("/api/chat/cli-login", { method: "POST" });
      const data = await res.json();
      const oauthUrl = data.oauth_url || data.url;
      if (oauthUrl) {
        window.open(oauthUrl, "_blank");
        setShowCodeInput(true);
        toast.info(
          "Complete login in the browser tab. Then paste the code below."
        );
      } else {
        toast.error("No OAuth URL returned");
      }
    } catch {
      toast.error("Failed to start CLI login");
    } finally {
      setLoggingIn(false);
    }
  };

  const handleCliLoginCode = async () => {
    if (!loginCode.trim()) return;
    try {
      const res = await fetch("/api/chat/cli-login-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: loginCode.trim() }),
      });
      if (res.ok) {
        toast.success("Claude CLI logged in");
        setLoginCode("");
        setShowCodeInput(false);
        const status = await fetch("/api/chat/provider-status").then((r) =>
          r.json()
        );
        setProviderStatus(status);
      } else {
        const data = await res.json();
        toast.error(data.error || "Login failed");
      }
    } catch {
      toast.error("Login code exchange failed");
    }
  };

  const handleSaveApiKey = async () => {
    if (!apiKey.trim()) return;
    setSavingKey(true);
    try {
      const res = await fetch("/api/orgs/default/api-key", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey.trim() }),
      });
      if (res.ok) {
        toast.success("API key saved");
        setApiKey("");
        const status = await fetch("/api/chat/provider-status").then((r) =>
          r.json()
        );
        setProviderStatus(status);
      } else {
        const data = await res.json();
        toast.error(data.error || "Failed to save key");
      }
    } catch {
      toast.error("Failed to save API key");
    } finally {
      setSavingKey(false);
    }
  };

  const refreshMembers = async () => {
    const res = await fetch(`/api/projects/${slug}/members`);
    if (res.ok) setMembers(await res.json());
  };

  const handleAddMember = async (userId: string, role: string) => {
    const res = await fetch(`/api/projects/${slug}/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, role }),
    });
    if (!res.ok) {
      const data = await res.json();
      toast.error(data.error || "Failed to add member");
      throw new Error("Failed to add member");
    }
    toast.success("Member added");
    await refreshMembers();
  };

  const handleRemoveMember = async (userId: string) => {
    const res = await fetch(`/api/projects/${slug}/members/${userId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      toast.error("Failed to remove member");
      return;
    }
    toast.success("Member removed");
    await refreshMembers();
  };

  const handleChangeRole = async (userId: string, role: string) => {
    const res = await fetch(`/api/projects/${slug}/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, role }),
    });
    if (!res.ok) {
      toast.error("Failed to change role");
      return;
    }
    toast.success("Role updated");
    await refreshMembers();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col">
        <TopBar variant="settings" projectName={slug} projectSlug={slug} onBack={() => router.push(`/projects/${slug}`)} />
        <LoadingOverlay />
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="min-h-screen flex flex-col">
        <TopBar variant="settings" projectName={slug} projectSlug={slug} onBack={() => router.push(`/projects/${slug}`)} />
        <div className="p-6 text-center text-muted-foreground">
          Failed to load settings.
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg)]">
      <TopBar variant="settings" projectName={slug} projectSlug={slug} onBack={() => router.push(`/projects/${slug}`)} />

      <main className="flex-1 overflow-y-auto flex justify-center">
        <div className="w-full max-w-[800px] px-8 py-12">
          {/* Breadcrumbs */}
          <nav className="flex items-center gap-2 text-[11px] font-mono text-muted-foreground uppercase tracking-widest mb-6">
            <span className="hover:text-foreground cursor-pointer" onClick={() => router.push('/projects')}>Projects</span>
            <ChevronRight className="h-3 w-3" />
            <span className="hover:text-foreground cursor-pointer" onClick={() => router.push(`/projects/${slug}`)}>{slug}</span>
            <ChevronRight className="h-3 w-3" />
            <span className="text-[var(--accent-light)]">Settings</span>
          </nav>

          <h1 className="text-3xl font-bold tracking-tight mb-10">Project Settings</h1>

          <div className="space-y-12">
            {/* ── General ── */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Settings className="h-4 w-4 text-muted-foreground" />
                <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">General</h2>
              </div>
              <div className="rounded-lg bg-[var(--surface)] p-6 border border-[var(--border-color)]">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">Comment auto-replies</h3>
                    <p className="text-sm text-muted-foreground mt-1">Enable AI-generated suggestions for PRD comment threads.</p>
                  </div>
                  <button
                    role="switch"
                    aria-checked={settings.claude_comment_replies}
                    onClick={() => update({ claude_comment_replies: !settings.claude_comment_replies })}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      settings.claude_comment_replies ? "bg-[var(--accent)]" : "bg-[var(--surface-high)]"
                    }`}
                  >
                    <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                      settings.claude_comment_replies ? "translate-x-6" : "translate-x-1"
                    }`} />
                  </button>
                </div>
              </div>
            </section>

            {/* ── Experimental Features ── */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <ExternalLink className="h-4 w-4 text-muted-foreground" />
                <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">Experimental Features</h2>
              </div>
              <div className="rounded-lg bg-[var(--surface)] p-6 border border-[var(--border-color)] space-y-8">
                {/* Chat toggle */}
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium">Chat Integration</h3>
                    <p className="text-sm text-muted-foreground mt-1">Directly chat with your document context using large language models.</p>
                  </div>
                  <button
                    role="switch"
                    aria-checked={settings.chat_enabled}
                    onClick={() => update({ chat_enabled: !settings.chat_enabled })}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      settings.chat_enabled ? "bg-[var(--accent)]" : "bg-[var(--surface-high)]"
                    }`}
                  >
                    <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                      settings.chat_enabled ? "translate-x-6" : "translate-x-1"
                    }`} />
                  </button>
                </div>

                {/* Provider + Model dropdowns */}
                <div className="grid grid-cols-2 gap-6 pt-6 border-t border-[var(--border-color)]">
                  <div>
                    <label className="block text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-2">Chat Provider</label>
                    <Select value={settings.chat_provider} onValueChange={(v) => update({ chat_provider: v })}>
                      <SelectTrigger className="bg-[var(--surface-dim)] border-[var(--border-color)]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {PROVIDERS.map((p) => (
                          <SelectItem key={p} value={p}>
                            {p === "claude_cli" ? "Claude CLI" : "Anthropic API"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="block text-[10px] font-mono uppercase tracking-widest text-muted-foreground mb-2">Chat Model</label>
                    <Select value={settings.chat_model} onValueChange={(v) => update({ chat_model: v })}>
                      <SelectTrigger className="bg-[var(--surface-dim)] border-[var(--border-color)]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {MODELS.map((m) => (
                          <SelectItem key={m} value={m}>
                            {m === "sonnet" ? "Claude 3.5 Sonnet" : m === "opus" ? "Claude 3 Opus" : "Claude 3 Haiku"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Provider Authentication — inline */}
                <div className="pt-6 border-t border-[var(--border-color)] space-y-5">
                  {/* Claude CLI status */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-mono uppercase tracking-widest text-muted-foreground">Claude CLI Status</h4>
                    <div className="flex items-center gap-2 text-sm">
                      {providerStatus?.claude_cli.installed ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500 shrink-0" />
                      )}
                      <span>{providerStatus?.claude_cli.installed ? "Installed" : "Not installed"}</span>
                      {providerStatus?.claude_cli.installed && (
                        <>
                          <span className="text-muted-foreground mx-1">&middot;</span>
                          {providerStatus?.claude_cli.logged_in ? (
                            <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                          ) : (
                            <XCircle className="h-4 w-4 text-muted-foreground shrink-0" />
                          )}
                          <span>{providerStatus?.claude_cli.logged_in ? "Logged in" : "Not logged in"}</span>
                        </>
                      )}
                    </div>
                    {providerStatus?.claude_cli.installed && (
                      <div className="space-y-2">
                        <Button variant="outline" size="sm" onClick={handleCliLogin} disabled={loggingIn} className="border-[var(--border-color)]">
                          <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                          {loggingIn ? "Opening..." : providerStatus.claude_cli.logged_in ? "Re-login" : "Login with Claude"}
                        </Button>
                        {showCodeInput && (
                          <div className="flex gap-2">
                            <Input placeholder="Paste auth code here..." value={loginCode} onChange={(e) => setLoginCode(e.target.value)} autoComplete="off" className="text-sm h-9 bg-[var(--surface-dim)] border-[var(--border-color)]" />
                            <Button size="sm" onClick={handleCliLoginCode} disabled={!loginCode.trim()}>Submit</Button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Anthropic API key */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-mono uppercase tracking-widest text-muted-foreground">Anthropic API Key</h4>
                    <div className="flex items-center gap-2 text-sm">
                      {providerStatus?.anthropic_api.configured ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                          <span>Configured</span>
                          <code className="text-[11px] font-mono text-[var(--accent-light)] bg-[var(--accent)]/5 px-1.5 py-0.5 rounded">{providerStatus.anthropic_api.key_hint}</code>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="text-muted-foreground">Not configured</span>
                        </>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Input placeholder="sk-ant-api03-..." value={apiKey} onChange={(e) => setApiKey(e.target.value)} type="password" className="text-sm h-9 bg-[var(--surface-dim)] border-[var(--border-color)]" />
                      <Button size="sm" onClick={handleSaveApiKey} disabled={!apiKey.trim() || savingKey}>
                        {savingKey ? "Saving..." : "Save Key"}
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* ── Members ── */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">Members</h2>
                </div>
              </div>
              <div className="rounded-lg bg-[var(--surface)] border border-[var(--border-color)] overflow-hidden">
                <MemberManager
                  members={members}
                  projectSlug={slug}
                  orgSlug={ORG_SLUG}
                  onAddMember={handleAddMember}
                  onRemoveMember={handleRemoveMember}
                  onChangeRole={handleChangeRole}
                />
              </div>
            </section>

            {/* ── API Keys ── */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Key className="h-4 w-4 text-muted-foreground" />
                  <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">API Keys</h2>
                </div>
                <button className="ui-placeholder bg-[var(--surface-high)] hover:bg-[var(--surface-highest)] text-foreground text-[11px] font-bold px-4 py-1.5 rounded transition-all flex items-center gap-2" disabled>
                  Generate New Key
                </button>
              </div>
              <div className="rounded-lg bg-[var(--surface)] border border-[var(--border-color)] overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-[var(--surface-high)]/50 border-b border-[var(--border-color)]">
                    <tr>
                      <th className="px-6 py-3 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Name</th>
                      <th className="px-6 py-3 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Key Prefix</th>
                      <th className="px-6 py-3 text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-color)]">
                    {providerStatus?.anthropic_api.configured ? (
                      <tr className="hover:bg-[var(--surface-high)]/30 transition-colors">
                        <td className="px-6 py-4 text-sm font-medium">Development Key</td>
                        <td className="px-6 py-4">
                          <code className="text-[11px] font-mono text-[var(--accent-light)] bg-[var(--accent)]/5 px-1.5 py-0.5 rounded">
                            {providerStatus.anthropic_api.key_hint}
                          </code>
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[var(--accent)]/10 text-[var(--accent-light)] text-[10px] font-bold uppercase tracking-wider">
                            <span className="w-1 h-1 rounded-full bg-[var(--accent-light)]" />
                            Active
                          </span>
                        </td>
                      </tr>
                    ) : (
                      <tr>
                        <td colSpan={3} className="px-6 py-8 text-center text-sm text-muted-foreground">No API keys configured</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Save button */}
            <div className="flex justify-end">
              <Button onClick={handleSave} disabled={saving} className="shadow-md shadow-[var(--accent)]/10">
                {saving ? "Saving..." : (
                  <><Check className="mr-1.5 h-4 w-4" />Save Settings</>
                )}
              </Button>
            </div>

            {/* ── Danger Zone ── */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="h-4 w-4 text-destructive" />
                <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-destructive">Danger Zone</h2>
              </div>
              <div className="border border-destructive/30 rounded-lg p-6 bg-destructive/5">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-medium">Delete Project</h3>
                    <p className="text-sm text-muted-foreground mt-1 max-w-lg">
                      Permanently delete this project and all associated PRDs, technical specs, and architecture diagrams. This action cannot be undone.
                    </p>
                  </div>
                  <Button variant="destructive" size="sm" className="shrink-0 ml-4 ui-placeholder shadow-lg shadow-destructive/10">
                    Delete Project
                  </Button>
                </div>
              </div>
            </section>
          </div>

          {/* Footer */}
          <div className="mt-20 pt-8 border-t border-[var(--border-color)] flex justify-between items-center text-[10px] font-mono text-muted-foreground uppercase tracking-[0.3em]">
            <span>Last Updated: {new Date().toISOString().slice(0, 10)}</span>
            <span>System Health: Nominal</span>
          </div>
        </div>
      </main>
    </div>
  );
}
