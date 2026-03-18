"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { TopBar } from "@/components/top-bar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LoadingOverlay } from "@/components/loading-overlay";
import { fetchSettings, updateSettings } from "@/lib/api";
import type { ProjectSettings } from "@/lib/types";

const PROVIDERS = ["openai", "anthropic", "local"];
const MODELS: Record<string, string[]> = {
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
  anthropic: ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"],
  local: ["llama-3", "mistral-7b"],
};

export default function SettingsPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const slug = params.slug;

  const [settings, setSettings] = useState<ProjectSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings(slug)
      .then(setSettings)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [slug]);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    try {
      const updated = await updateSettings(slug, settings);
      setSettings(updated);
    } catch (err) {
      console.error("Failed to save settings:", err);
    } finally {
      setSaving(false);
    }
  };

  const update = (patch: Partial<ProjectSettings>) => {
    setSettings((prev) => (prev ? { ...prev, ...patch } : prev));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col">
        <TopBar projectName="..." sectionTitle="Settings" />
        <LoadingOverlay />
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="min-h-screen flex flex-col">
        <TopBar />
        <div className="p-6 text-center text-muted-foreground">
          Failed to load settings.
        </div>
      </div>
    );
  }

  const availableModels = MODELS[settings.llm_provider] ?? [];

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar projectName="Project" sectionTitle="Settings" />

      <main className="flex-1 p-6">
        <div className="max-w-2xl mx-auto space-y-6">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push(`/projects/${slug}`)}
            >
              <ArrowLeft className="mr-1.5 h-4 w-4" />
              Back
            </Button>
          </div>

          <h1 className="text-2xl font-bold">Project Settings</h1>

          {/* Features */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Features</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">
                    Comment Replies
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Enable AI-powered comment reply suggestions
                  </p>
                </div>
                <button
                  role="switch"
                  aria-checked={settings.comment_replies_enabled}
                  onClick={() =>
                    update({
                      comment_replies_enabled:
                        !settings.comment_replies_enabled,
                    })
                  }
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.comment_replies_enabled
                      ? "bg-primary"
                      : "bg-muted"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                      settings.comment_replies_enabled
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
                    Enable the AI chat panel for this project
                  </p>
                </div>
                <button
                  role="switch"
                  aria-checked={settings.chat_enabled}
                  onClick={() =>
                    update({
                      chat_enabled: !settings.chat_enabled,
                    })
                  }
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    settings.chat_enabled
                      ? "bg-primary"
                      : "bg-muted"
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

          {/* LLM Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                LLM Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label
                  htmlFor="provider"
                  className="text-sm font-medium"
                >
                  Provider
                </label>
                <Select
                  value={settings.llm_provider}
                  onValueChange={(value) =>
                    update({
                      llm_provider: value,
                      llm_model:
                        MODELS[value]?.[0] ??
                        settings.llm_model,
                    })
                  }
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PROVIDERS.map((p) => (
                      <SelectItem key={p} value={p}>
                        {p.charAt(0).toUpperCase() + p.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label
                  htmlFor="model"
                  className="text-sm font-medium"
                >
                  Model
                </label>
                <Select
                  value={settings.llm_model}
                  onValueChange={(value) =>
                    update({ llm_model: value })
                  }
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {availableModels.map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-end">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save Settings"}
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
