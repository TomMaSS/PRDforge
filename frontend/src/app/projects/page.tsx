"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FolderOpen, Plus, Check } from "lucide-react";
import { TopBar } from "@/components/top-bar";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/components/empty-state";
import { LoadingOverlay } from "@/components/loading-overlay";
import { fetchProjects, createProject, fetchTemplates } from "@/lib/api";
import type { TemplateInfo } from "@/lib/api";
import type { Project } from "@/lib/types";

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

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />

      <main className="flex-1 p-6">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold">Projects</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Manage your product requirement documents
              </p>
            </div>

            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4" />
                  New Project
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Create Project</DialogTitle>
                  <DialogDescription>
                    Choose a template and create a new PRD project.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  {/* Template selector */}
                  <div>
                    <label className="text-sm font-medium">Template</label>
                    <div className="grid grid-cols-2 gap-2 mt-1.5">
                      {templates.map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => setTemplateId(t.id)}
                          className={`relative rounded-lg border p-3 text-left text-sm transition-colors hover:bg-accent ${
                            templateId === t.id
                              ? "border-primary bg-primary/5"
                              : "border-border"
                          }`}
                        >
                          {templateId === t.id && (
                            <Check className="absolute top-2 right-2 h-3.5 w-3.5 text-primary" />
                          )}
                          <div className="font-medium">{t.name}</div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            {t.description}
                          </div>
                          {t.section_count > 0 && (
                            <div className="text-xs text-muted-foreground mt-1">
                              {t.section_count} sections
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label
                      htmlFor="project-name"
                      className="text-sm font-medium"
                    >
                      Name
                    </label>
                    <Input
                      id="project-name"
                      placeholder="My Product PRD"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="mt-1.5"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="project-description"
                      className="text-sm font-medium"
                    >
                      Description
                    </label>
                    <Textarea
                      id="project-description"
                      placeholder="Brief description of the project..."
                      value={description}
                      onChange={(e) =>
                        setDescription(e.target.value)
                      }
                      className="mt-1.5"
                      rows={3}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => setDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleCreate}
                    disabled={!name.trim() || creating}
                  >
                    {creating ? "Creating..." : "Create"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

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
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {projects.map((project) => (
                <Card
                  key={project.slug}
                  className="cursor-pointer transition-shadow hover:shadow-md"
                  onClick={() =>
                    router.push(`/projects/${project.slug}`)
                  }
                >
                  <CardHeader>
                    <CardTitle className="text-base">
                      {project.name}
                    </CardTitle>
                    {project.description && (
                      <CardDescription className="line-clamp-2">
                        {project.description}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>
                        {project.section_count}{" "}
                        {project.section_count === 1
                          ? "section"
                          : "sections"}
                      </span>
                      <span>
                        {project.total_words} words
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
