"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Settings, FileText, GitBranch, Clock, BarChart3 } from "lucide-react";
import { TopBar } from "@/components/top-bar";
import { SectionSidebar } from "@/components/section-sidebar";
import { SectionViewer } from "@/components/section-viewer";
import { ChatPanel } from "@/components/chat-panel";
import { DependencyGraph } from "@/components/dependency-graph";
import { TokenStatsDashboard } from "@/components/token-stats-dashboard";
import { EmptyState } from "@/components/empty-state";
import { LoadingOverlay } from "@/components/loading-overlay";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  fetchProject,
  fetchSection,
  fetchChangelog,
  fetchTokenStats,
} from "@/lib/api";
import type {
  ProjectDetail,
  SectionDetail,
  ChangelogEntry,
  ChatMessage,
  TokenStats,
} from "@/lib/types";

export default function ProjectDetailPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const slug = params.slug;

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [activeSection, setActiveSection] = useState<SectionDetail | null>(null);
  const [changelog, setChangelog] = useState<ChangelogEntry[]>([]);
  const [tokenStats, setTokenStats] = useState<TokenStats | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [sectionLoading, setSectionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("sections");

  useEffect(() => {
    fetchProject(slug)
      .then((p) => {
        setProject(p);
        if (p.sections.length > 0) {
          handleSectionSelect(p.sections[0].slug);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  const handleSectionSelect = useCallback(
    async (sectionSlug: string) => {
      setSectionLoading(true);
      try {
        const section = await fetchSection(slug, sectionSlug);
        setActiveSection(section);
      } catch (err) {
        console.error("Failed to load section:", err);
      } finally {
        setSectionLoading(false);
      }
    },
    [slug]
  );

  const handleTabChange = useCallback(
    async (tab: string) => {
      setActiveTab(tab);
      if (tab === "changelog" && changelog.length === 0) {
        try {
          const entries = await fetchChangelog(slug);
          setChangelog(entries);
        } catch (err) {
          console.error("Failed to load changelog:", err);
        }
      }
      if (tab === "stats" && !tokenStats) {
        try {
          const stats = await fetchTokenStats(slug);
          setTokenStats(stats);
        } catch (err) {
          console.error("Failed to load token stats:", err);
        }
      }
    },
    [slug, changelog.length, tokenStats]
  );

  const handleChatSend = useCallback((content: string) => {
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setChatMessages((prev) => [...prev, userMsg]);
    // Streaming response will be implemented in a future phase
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col">
        <TopBar />
        <LoadingOverlay />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen flex flex-col">
        <TopBar />
        <EmptyState
          icon={FileText}
          title="Project not found"
          description="The project you are looking for does not exist."
          action={{
            label: "Back to Projects",
            onClick: () => router.push("/projects"),
          }}
        />
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <TopBar
        projectName={project.name}
        sectionTitle={activeSection?.title}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Main area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <Tabs
            value={activeTab}
            onValueChange={handleTabChange}
            className="flex flex-1 flex-col overflow-hidden"
          >
            <div className="flex items-center justify-between border-b px-6 py-2">
              <TabsList>
                <TabsTrigger value="sections">
                  <FileText className="mr-1.5 h-4 w-4" />
                  Sections
                </TabsTrigger>
                <TabsTrigger value="dependencies">
                  <GitBranch className="mr-1.5 h-4 w-4" />
                  Dependencies
                </TabsTrigger>
                <TabsTrigger value="changelog">
                  <Clock className="mr-1.5 h-4 w-4" />
                  Changelog
                </TabsTrigger>
                <TabsTrigger value="stats">
                  <BarChart3 className="mr-1.5 h-4 w-4" />
                  Stats
                </TabsTrigger>
              </TabsList>

              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  router.push(`/projects/${slug}/settings`)
                }
              >
                <Settings className="mr-1.5 h-4 w-4" />
                Settings
              </Button>
            </div>

            <TabsContent
              value="sections"
              className="flex flex-1 overflow-hidden mt-0"
            >
              <SectionSidebar
                sections={project.sections}
                activeSlug={activeSection?.slug}
                onSelect={handleSectionSelect}
              />

              {sectionLoading ? (
                <LoadingOverlay />
              ) : activeSection ? (
                <SectionViewer section={activeSection} />
              ) : (
                <EmptyState
                  icon={FileText}
                  title="No sections"
                  description="This project has no sections yet. Create one to get started."
                  className="flex-1"
                />
              )}
            </TabsContent>

            <TabsContent
              value="dependencies"
              className="flex-1 overflow-auto p-6 mt-0"
            >
              <DependencyGraph />
            </TabsContent>

            <TabsContent
              value="changelog"
              className="flex-1 overflow-auto p-6 mt-0"
            >
              {changelog.length === 0 ? (
                <EmptyState
                  icon={Clock}
                  title="No changelog entries"
                  description="Changes to sections will appear here."
                />
              ) : (
                <div className="max-w-3xl mx-auto space-y-3">
                  {changelog.map((entry) => (
                    <div
                      key={entry.id}
                      className="flex items-start gap-3 rounded-lg border p-3"
                    >
                      <div className="flex-1">
                        <p className="text-sm">
                          <span className="font-medium">
                            {entry.action}
                          </span>{" "}
                          <span className="text-muted-foreground">
                            {entry.target}
                          </span>
                        </p>
                        {entry.detail && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {entry.detail}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(
                          entry.created_at
                        ).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent
              value="stats"
              className="flex-1 overflow-auto p-6 mt-0"
            >
              {tokenStats ? (
                <div className="max-w-4xl mx-auto">
                  <TokenStatsDashboard stats={tokenStats} />
                </div>
              ) : (
                <LoadingOverlay />
              )}
            </TabsContent>
          </Tabs>
        </div>

        {/* Chat panel */}
        {project.settings.chat_enabled && (
          <ChatPanel
            projectSlug={slug}
            messages={chatMessages}
            onSend={handleChatSend}
          />
        )}
      </div>
    </div>
  );
}
