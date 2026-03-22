"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  XCircle,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { TopBar } from "@/components/top-bar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
        <TopBar projectName={slug} sectionTitle="Settings" />
        <LoadingOverlay />
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="min-h-screen flex flex-col">
        <TopBar projectName={slug} sectionTitle="Settings" />
        <div className="p-6 text-center text-muted-foreground">
          Failed to load settings.
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar projectName={slug} sectionTitle="Settings" />

      <main className="flex-1 p-6">
        <div className="max-w-2xl mx-auto space-y-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/projects/${slug}`)}
          >
            <ArrowLeft className="mr-1.5 h-4 w-4" />
            Back
          </Button>

          <h1 className="text-2xl font-bold">Project Settings</h1>

          {/* Features */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Features</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Comment Auto-Replies</p>
                  <p className="text-xs text-muted-foreground">
                    Claude auto-replies when resolving comments
                  </p>
                </div>
                <button
                  role="switch"
                  aria-checked={settings.claude_comment_replies}
                  onClick={() =>
                    update({
                      claude_comment_replies: !settings.claude_comment_replies,
                    })
                  }
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.claude_comment_replies
                      ? "bg-primary"
                      : "bg-secondary"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                      settings.claude_comment_replies
                        ? "translate-x-6"
                        : "translate-x-1"
                    }`}
                  />
                </button>
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Chat Panel</p>
                  <p className="text-xs text-muted-foreground">
                    Enable AI chat for this project
                  </p>
                </div>
                <button
                  role="switch"
                  aria-checked={settings.chat_enabled}
                  onClick={() =>
                    update({ chat_enabled: !settings.chat_enabled })
                  }
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.chat_enabled ? "bg-primary" : "bg-secondary"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                      settings.chat_enabled
                        ? "translate-x-6"
                        : "translate-x-1"
                    }`}
                  />
                </button>
              </div>
            </CardContent>
          </Card>

          {/* Chat Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Chat Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Provider</label>
                <Select
                  value={settings.chat_provider}
                  onValueChange={(v) => update({ chat_provider: v })}
                >
                  <SelectTrigger className="mt-1.5">
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
                <label className="text-sm font-medium">Model</label>
                <Select
                  value={settings.chat_model}
                  onValueChange={(v) => update({ chat_model: v })}
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MODELS.map((m) => (
                      <SelectItem key={m} value={m}>
                        {m.charAt(0).toUpperCase() + m.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Provider Authentication */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Provider Authentication
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Claude CLI */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium">Claude CLI</h4>
                <div className="flex items-center gap-2 text-sm">
                  {providerStatus?.claude_cli.installed ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-500 shrink-0" />
                  )}
                  <span>
                    {providerStatus?.claude_cli.installed
                      ? "Installed"
                      : "Not installed"}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  {providerStatus?.claude_cli.logged_in ? (
                    <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                  ) : (
                    <XCircle className="h-4 w-4 text-muted-foreground shrink-0" />
                  )}
                  <span>
                    {providerStatus?.claude_cli.logged_in
                      ? "Logged in"
                      : "Not logged in"}
                  </span>
                </div>
                {providerStatus?.claude_cli.installed && (
                    <div className="space-y-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleCliLogin}
                        disabled={loggingIn}
                      >
                        <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                        {loggingIn
                          ? "Opening..."
                          : providerStatus.claude_cli.logged_in
                            ? "Re-login"
                            : "Login with Claude"}
                      </Button>
                      {showCodeInput && (
                        <div className="flex gap-2">
                          <Input
                            placeholder="Paste auth code here..."
                            value={loginCode}
                            onChange={(e) => setLoginCode(e.target.value)}
                            autoComplete="off"
                            className="text-sm h-9"
                          />
                          <Button
                            size="sm"
                            onClick={handleCliLoginCode}
                            disabled={!loginCode.trim()}
                          >
                            Submit
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
              </div>

              {/* Divider */}
              <div className="border-t" />

              {/* Anthropic API */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium">Anthropic API Key</h4>
                <div className="flex items-center gap-2 text-sm">
                  {providerStatus?.anthropic_api.configured ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                      <span>
                        Configured (
                        {providerStatus.anthropic_api.key_hint})
                      </span>
                    </>
                  ) : (
                    <>
                      <XCircle className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="text-muted-foreground">
                        Not configured
                      </span>
                    </>
                  )}
                </div>
                <div className="flex gap-2">
                  <Input
                    placeholder="sk-ant-api03-..."
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    type="password"
                    className="text-sm h-9"
                  />
                  <Button
                    size="sm"
                    onClick={handleSaveApiKey}
                    disabled={!apiKey.trim() || savingKey}
                  >
                    {savingKey ? "Saving..." : "Save Key"}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Members */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Members</CardTitle>
            </CardHeader>
            <CardContent>
              <MemberManager
                members={members}
                projectSlug={slug}
                orgSlug={ORG_SLUG}
                onAddMember={handleAddMember}
                onRemoveMember={handleRemoveMember}
                onChangeRole={handleChangeRole}
              />
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? (
                "Saving..."
              ) : (
                <>
                  <Check className="mr-1.5 h-4 w-4" />
                  Save Settings
                </>
              )}
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
