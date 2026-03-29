"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FolderOpen,
  Plus,
  Check,
  FileText,
  Layers,
  Smartphone,
  Code2,
} from "lucide-react";
import { TopBar } from "@/components/top-bar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/empty-state";
import { LoadingOverlay } from "@/components/loading-overlay";
import { fetchProjects, createProject, fetchTemplates } from "@/lib/api";
import type { TemplateInfo } from "@/lib/api";
import type { Project } from "@/lib/types";

const TEMPLATE_ICONS: Record<string, typeof FileText> = {
  blank: FileText,
  "saas-mvp": Layers,
  "mobile-app": Smartphone,
  "api-design": Code2,
};

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [templateId, setTemplateId] = useState("blank");
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchProjects()
      .then(setProjects)
      .catch(console.error)
      .finally(() => setLoading(false));
    fetchTemplates().then(setTemplates).catch(console.error);
  }, []);

  const handleCreate = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      const project = await createProject({
        name: name.trim(),
        description: description.trim(),
        template_id: templateId,
      });
      setProjects((prev) => [...prev, project]);
      setDialogOpen(false);
      setName("");
      setDescription("");
      setTemplateId("blank");
      router.push(`/projects/${project.slug}`);
    } catch (err) {
      console.error("Failed to create project:", err);
    } finally {
      setCreating(false);
    }
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg)]">
      <TopBar variant="dashboard" />

      <main className="flex-1 p-6 md:p-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Projects</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Manage your product requirement documents and engineering blueprints.
              </p>
            </div>

            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button className="gap-1.5 shadow-md shadow-[var(--accent)]/10">
                  <Plus className="h-4 w-4" />
                  New Project
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg border-[var(--border-color)] bg-[var(--surface-high)]">
                <DialogHeader>
                  <DialogTitle className="text-lg">Forge New Project</DialogTitle>
                  <DialogDescription>
                    Select a starting point for your technical documentation.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-5 py-4">
                  {/* Blueprints & Templates */}
                  <div>
                    <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">
                      Blueprints &amp; Templates
                    </label>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {templates.map((t) => {
                        const Icon = TEMPLATE_ICONS[t.id] || FileText;
                        const isActive = templateId === t.id;
                        return (
                          <button
                            key={t.id}
                            type="button"
                            onClick={() => setTemplateId(t.id)}
                            className={`relative flex flex-col items-center gap-2 rounded-lg border p-4 text-center text-sm transition-all ${
                              isActive
                                ? "border-[var(--accent)] bg-[var(--accent)]/10 shadow-sm shadow-[var(--accent)]/10"
                                : "border-[var(--border-color)] hover:border-[var(--accent)]/40 hover:bg-[var(--surface)]"
                            }`}
                          >
                            {isActive && (
                              <Check className="absolute top-2 right-2 h-3 w-3 text-[var(--accent)]" />
                            )}
                            <Icon className={`h-5 w-5 ${isActive ? "text-[var(--accent)]" : "text-muted-foreground"}`} />
                            <span className="font-medium text-xs">{t.name}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Project Name */}
                  <div>
                    <label
                      htmlFor="project-name"
                      className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                    >
                      Project Name
                    </label>
                    <input
                      id="project-name"
                      placeholder="e.g., Artemis Data Pipeline"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="input-etched w-full rounded-lg px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50"
                    />
                  </div>

                  {/* Description */}
                  <div>
                    <label
                      htmlFor="project-description"
                      className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-muted-foreground"
                    >
                      High-level Description
                    </label>
                    <textarea
                      id="project-description"
                      placeholder="Summarize the technical vision and core objectives..."
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      className="input-etched w-full rounded-lg px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 resize-none"
                      rows={3}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setDialogOpen(false)}
                    className="border-[var(--border-color)]"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleCreate}
                    disabled={!name.trim() || creating}
                    className="shadow-md shadow-[var(--accent)]/10"
                  >
                    {creating ? "Creating..." : "Create Project"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {/* Content */}
          {loading ? (
            <LoadingOverlay />
          ) : projects.length === 0 ? (
            <EmptyState
              icon={FolderOpen}
              title="No projects yet"
              description="Create your first PRD project to get started with structured requirements management."
              action={{
                label: "Create Project",
                onClick: () => setDialogOpen(true),
              }}
            />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {projects.map((project) => (
                <div
                  key={project.slug}
                  onClick={() => router.push(`/projects/${project.slug}`)}
                  className="group cursor-pointer rounded-xl border border-[var(--border-color)] bg-[var(--card-bg)] p-5 transition-all hover:border-[var(--accent)]/30 hover:shadow-lg hover:shadow-[var(--accent)]/5"
                >
                  <div className="mb-3">
                    <h3 className="font-semibold text-foreground group-hover:text-[var(--accent-light)] transition-colors">
                      {project.name}
                    </h3>
                    {project.description && (
                      <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                        {project.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-3 border-t border-[var(--border-color)]">
                    <div className="flex items-center gap-3">
                      <span className="tabular-nums">
                        {project.section_count}{" "}
                        {project.section_count === 1 ? "section" : "sections"}
                      </span>
                      <span className="tabular-nums">
                        {project.total_words.toLocaleString()} words
                      </span>
                    </div>
                    <span>{formatDate(project.updated_at)}</span>
                  </div>
                </div>
              ))}

              {/* Dashed "Create New Project" card */}
              <div
                onClick={() => setDialogOpen(true)}
                className="flex cursor-pointer items-center justify-center rounded-xl border-2 border-dashed border-[var(--border-color)] p-5 text-muted-foreground transition-all hover:border-[var(--accent)]/40 hover:text-[var(--accent-light)]"
              >
                <div className="text-center">
                  <Plus className="mx-auto h-8 w-8 mb-2 opacity-50" />
                  <span className="text-sm font-medium">Create New Project</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
