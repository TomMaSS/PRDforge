"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  FileText,
  GitBranch,
  Clock,
  BarChart3,
  MessageSquare,
  Eye,
  Download,
  FileDown,
} from "lucide-react";
import { TopBar } from "@/components/top-bar";
import { SectionSidebar } from "@/components/section-sidebar";
import { SectionViewer } from "@/components/section-viewer";
import { ChatPanel } from "@/components/chat-panel";
import { DependencyGraph } from "@/components/dependency-graph";
import { TokenStatsDashboard } from "@/components/token-stats-dashboard";
import { EmptyState } from "@/components/empty-state";
import { LoadingOverlay } from "@/components/loading-overlay";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { MarkdownRenderer } from "@/components/markdown-renderer";
import { fetchProject, fetchSection, fetchTokenStats } from "@/lib/api";
import type {
  ProjectDetailResponse,
  SectionDetailResponse,
  TokenStats,
  ProjectSettings,
} from "@/lib/types";

interface AllComment {
  id: string;
  anchor_text: string;
  body: string;
  resolved: boolean;
  created_at: string;
  section_slug: string;
  section_title: string;
}

export default function ProjectDetailPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const slug = params.slug;

  const [project, setProject] = useState<ProjectDetailResponse | null>(null);
  const [activeSection, setActiveSection] =
    useState<SectionDetailResponse | null>(null);
  const [tokenStats, setTokenStats] = useState<TokenStats | null>(null);
  const [settings, setSettings] = useState<ProjectSettings | null>(null);
  const [allComments, setAllComments] = useState<AllComment[]>([]);
  const [chatMessages, setChatMessages] = useState<
    { id: string; role: "user" | "assistant"; content: string; created_at: string; context?: string; tools?: string[] }[]
  >([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamStatus, setStreamStatus] = useState<string>("");
  const [streamTools, setStreamTools] = useState<string[]>([]);
  const [pendingApproval, setPendingApproval] = useState<{ messageId: string; tools: string[] } | null>(null);
  const streamStatusRef = useRef("");
  const abortRef = useRef<AbortController | null>(null);
  const [selectionContext, setSelectionContext] = useState<{
    selected_text: string;
    section_slug: string;
    section_title: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [sectionLoading, setSectionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("sections");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState("");

  const loadComments = useCallback(async () => {
    try {
      const res = await fetch(`/api/projects/${slug}/comments`);
      if (res.ok) {
        const data = await res.json();
        setAllComments(data);
      }
    } catch {
      /* ignore */
    }
  }, [slug]);

  useEffect(() => {
    Promise.all([
      fetchProject(slug),
      fetch(`/api/projects/${slug}/settings`).then((r) => r.json()),
    ])
      .then(([p, s]) => {
        setProject(p);
        setSettings(s);
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
        const data = await fetchSection(slug, sectionSlug);
        setActiveSection(data);
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
      if (tab === "stats" && !tokenStats) {
        try {
          const stats = await fetchTokenStats(slug);
          setTokenStats(stats);
        } catch (err) {
          console.error("Failed to load token stats:", err);
        }
      }
      if (tab === "comments") {
        loadComments();
      }
    },
    [slug, tokenStats, loadComments]
  );

  // Load chat messages
  useEffect(() => {
    if (!settings?.chat_enabled) return;
    fetch(`/api/projects/${slug}/chat/messages`)
      .then((r) => r.json())
      .then((data) => {
        // API returns {messages: [...]} not a plain array
        const msgs = Array.isArray(data) ? data : data.messages || [];
        setChatMessages(
          msgs.map((m: Record<string, unknown>) => {
            const meta = (m.metadata || {}) as Record<string, unknown>;
            const sc = meta.selection_context as Record<string, string> | undefined;
            const toolEvts = (meta.tool_events || []) as { name: string }[];
            return {
              id: m.id as string,
              role: m.role as "user" | "assistant",
              content: m.content as string,
              created_at: m.created_at as string,
              context: sc?.selected_text || undefined,
              tools: toolEvts.length > 0 ? toolEvts.map((t) => t.name) : undefined,
            };
          })
        );
      })
      .catch(() => {});
  }, [slug, settings?.chat_enabled]);

  const handleChatSend = useCallback(
    async (content: string, attachments?: { name: string; type: string; text_content: string }[]) => {
      // Add user message optimistically, include selection context
      const userMsg = {
        id: crypto.randomUUID(),
        role: "user" as const,
        content,
        created_at: new Date().toISOString(),
        context: selectionContext?.selected_text || undefined,
      };
      setChatMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      setStreamStatus("thinking");
      streamStatusRef.current = "thinking";
      setStreamTools([]);

      const abort = new AbortController();
      abortRef.current = abort;

      try {
        const body: Record<string, unknown> = { message: content };
        if (selectionContext) {
          body.selection_context = {
            selected_text: selectionContext.selected_text,
            section_slug: selectionContext.section_slug,
            section_title: selectionContext.section_title,
          };
        }
        if (attachments && attachments.length > 0) {
          body.attachments = attachments;
        }

        const res = await fetch(`/api/projects/${slug}/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: abort.signal,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ error: "Chat failed" }));
          setChatMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: `Error: ${err.error || res.statusText}`,
              created_at: new Date().toISOString(),
            },
          ]);
          return;
        }

        // Read SSE stream
        const reader = res.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let assistantContent = "";
        const assistantId = crypto.randomUUID();
        let buffer = "";

        // Add empty assistant message
        setChatMessages((prev) => [
          ...prev,
          { id: assistantId, role: "assistant", content: "", created_at: new Date().toISOString() },
        ]);

        while (true) {
          // Timeout: if no data for 2 minutes, break out
          const readPromise = reader.read();
          const timeout = new Promise<{ done: true; value: undefined }>((resolve) =>
            setTimeout(() => resolve({ done: true, value: undefined }), 120_000)
          );
          const { done, value } = await Promise.race([readPromise, timeout]);
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE blocks (separated by \n\n or \r\n\r\n)
          const blocks = buffer.split(/\r?\n\r?\n/);
          buffer = blocks.pop() || ""; // Keep incomplete block in buffer

          for (const block of blocks) {
            if (!block.trim()) continue;
            const lines = block.split(/\r?\n/);
            let eventType = "";
            let eventData = "";
            for (const line of lines) {
              if (line.startsWith("event:")) eventType = line.slice(6).trim();
              if (line.startsWith("data:")) eventData = line.slice(5).trim();
            }
            if (!eventData) continue;

            try {
              const parsed = JSON.parse(eventData);
              if (eventType === "status" && parsed.phase) {
                setStreamStatus(parsed.phase);
                streamStatusRef.current = parsed.phase;
              } else if (eventType === "tool" && parsed.name) {
                setStreamTools((prev) => [...prev, parsed.name]);
                setStreamStatus(`Using: ${parsed.name.replace(/^mcp__prd-forge__/, "").replace(/_/g, " ")}`);
                streamStatusRef.current = "tool_use";
              } else if (eventType === "delta" && parsed.text) {
                if (streamStatusRef.current !== "writing") {
                  setStreamStatus("writing");
                  streamStatusRef.current = "writing";
                }
                assistantContent += parsed.text;
                setChatMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, content: assistantContent } : m
                  )
                );
              } else if (eventType === "approval") {
                // Tool needs approval — show approval UI
                const toolName = parsed.name || parsed.tool || "unknown tool";
                setStreamStatus("approval");
                streamStatusRef.current = "approval";
                // Will be handled after stream ends via metadata
              } else if (eventType === "error") {
                // Backend error — show to user
                const errMsg = parsed.error || "Chat stream failed";
                setChatMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, content: `Error: ${errMsg}` } : m
                  )
                );
              } else if (eventType === "done" && parsed.message) {
                // Final message — use the server's complete content + tool events
                assistantContent = parsed.message.content;
                const meta = parsed.message.metadata || {};
                const toolEvents = (meta.tool_events || []).map((t: { name: string }) => t.name);
                const approvalReqs = meta.approval_requests || [];
                const needsApproval = !meta.approval_resolved && approvalReqs.length > 0;
                setChatMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, id: parsed.message.id, content: assistantContent, tools: toolEvents.length > 0 ? toolEvents : undefined }
                      : m
                  )
                );
                if (needsApproval) {
                  setPendingApproval({
                    messageId: parsed.message.id,
                    tools: approvalReqs.map((a: { name?: string; tool?: string }) => a.name || a.tool || "tool"),
                  });
                }
              }
            } catch {
              // ignore unparseable events
            }
          }
        }
      } catch (err) {
        setChatMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: `Error: ${err instanceof Error ? err.message : "Connection failed"}`,
            created_at: new Date().toISOString(),
          },
        ]);
      } finally {
        setIsStreaming(false);
        setStreamStatus("");
        setStreamTools([]);
        setSelectionContext(null);
        // Auto-refresh active section + project (Claude may have edited content)
        if (activeSection) {
          handleSectionSelect(activeSection.section.slug);
        }
        fetchProject(slug).then(setProject).catch(() => {});
      }
    },
    [slug, selectionContext]
  );

  const handleChatStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const handleApprove = useCallback(
    async (messageId: string) => {
      setPendingApproval(null);
      setIsStreaming(true);
      setStreamStatus("thinking");
      streamStatusRef.current = "thinking";
      setStreamTools([]);

      const abort = new AbortController();
      abortRef.current = abort;

      try {
        const res = await fetch(`/api/projects/${slug}/chat/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ assistant_message_id: messageId }),
          signal: abort.signal,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ error: "Approve failed" }));
          setChatMessages((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: "assistant", content: `Error: ${err.error || res.statusText}`, created_at: new Date().toISOString() },
          ]);
          return;
        }

        const reader = res.body?.getReader();
        if (!reader) return;

        const decoder = new TextDecoder();
        let assistantContent = "";
        const assistantId = crypto.randomUUID();
        let buffer = "";

        setChatMessages((prev) => [
          ...prev,
          { id: assistantId, role: "assistant", content: "", created_at: new Date().toISOString() },
        ]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split(/\r?\n\r?\n/);
          buffer = blocks.pop() || "";
          for (const block of blocks) {
            if (!block.trim()) continue;
            const lines = block.split(/\r?\n/);
            let eventType = "";
            let eventData = "";
            for (const line of lines) {
              if (line.startsWith("event:")) eventType = line.slice(6).trim();
              if (line.startsWith("data:")) eventData = line.slice(5).trim();
            }
            if (!eventData) continue;
            try {
              const parsed = JSON.parse(eventData);
              if (eventType === "delta" && parsed.text) {
                assistantContent += parsed.text;
                setChatMessages((prev) =>
                  prev.map((m) => (m.id === assistantId ? { ...m, content: assistantContent } : m))
                );
              } else if (eventType === "tool" && parsed.name) {
                setStreamTools((prev) => [...prev, parsed.name]);
              } else if (eventType === "error") {
                const errMsg = parsed.error || "Chat stream failed";
                setChatMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, content: `Error: ${errMsg}` } : m
                  )
                );
              } else if (eventType === "done" && parsed.message) {
                assistantContent = parsed.message.content;
                const meta = parsed.message.metadata || {};
                const toolEvents = (meta.tool_events || []).map((t: { name: string }) => t.name);
                setChatMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, id: parsed.message.id, content: assistantContent, tools: toolEvents.length > 0 ? toolEvents : undefined }
                      : m
                  )
                );
              }
            } catch { /* ignore */ }
          }
        }
      } catch { /* aborted or error */ } finally {
        setIsStreaming(false);
        setStreamStatus("");
        setStreamTools([]);
        if (activeSection) handleSectionSelect(activeSection.section.slug);
        fetchProject(slug).then(setProject).catch(() => {});
      }
    },
    [slug, activeSection, handleSectionSelect]
  );

  // Called when text is selected in SectionViewer — injects into chat
  const handleSelectionContext = useCallback(
    (text: string) => {
      if (activeSection) {
        setSelectionContext({
          selected_text: text,
          section_slug: activeSection.section.slug,
          section_title: activeSection.section.title,
        });
      }
    },
    [activeSection]
  );

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col">
        <TopBar variant="project" activeTab="sections" projectSlug={slug} />
        <LoadingOverlay />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen flex flex-col">
        <TopBar variant="project" activeTab="sections" projectSlug={slug} />
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
        variant="project"
        activeTab={activeTab}
        onTabChange={handleTabChange}
        projectName={project.project.name}
        projectSlug={slug}
      />

      <div className="flex flex-1 overflow-hidden bg-[var(--bg)]">
        <div className="flex flex-1 flex-col overflow-hidden">
          <Tabs
            value={activeTab}
            onValueChange={handleTabChange}
            className="flex flex-1 flex-col overflow-hidden"
          >
            {/* Action bar — compact export controls */}
            <div className="flex items-center justify-end border-b border-[var(--border-color)] px-4 py-1.5 bg-[var(--card-bg)]">
              <div className="flex items-center gap-0.5">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                  onClick={async () => {
                    const res = await fetch(`/api/projects/${slug}/export`);
                    if (res.ok) {
                      setPreviewContent(await res.text());
                      setPreviewOpen(true);
                    }
                  }}
                >
                  <Eye className="mr-1 h-3.5 w-3.5" />
                  Preview
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                  onClick={() => {
                    const a = document.createElement("a");
                    a.href = `/api/projects/${slug}/export`;
                    a.download = `${slug}.md`;
                    a.click();
                  }}
                >
                  <Download className="mr-1 h-3.5 w-3.5" />
                  .md
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2.5 text-xs text-muted-foreground hover:text-foreground"
                  onClick={async () => {
                    const res = await fetch(`/api/projects/${slug}/export`);
                    if (!res.ok) return;
                    const md = await res.text();
                    // Render markdown to HTML via the same preview path
                    const tmp = document.createElement("div");
                    tmp.style.display = "none";
                    document.body.appendChild(tmp);
                    // Use ReactDOM to render markdown
                    const { createRoot } = await import("react-dom/client");
                    const { MarkdownRenderer: MR } = await import("@/components/markdown-renderer");
                    const { createElement: h } = await import("react");
                    const root = createRoot(tmp);
                    root.render(h(MR, { content: md }));
                    // Wait for render
                    await new Promise((r) => setTimeout(r, 300));
                    const html = tmp.innerHTML;
                    root.unmount();
                    tmp.remove();
                    const win = window.open("", "_blank");
                    if (!win) return;
                    const title = project?.project.name ?? "PRD";
                    win.document.write(`<!DOCTYPE html>
<html><head><title>${title}</title>
<style>
  *, *::before, *::after { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; line-height: 1.6; }
  h1 { font-size: 1.8rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.5rem; }
  h2 { font-size: 1.4rem; margin-top: 2rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3rem; }
  h3 { font-size: 1.15rem; margin-top: 1.5rem; }
  pre { background: #f3f4f6; border-radius: 6px; padding: 1rem; overflow-x: auto; font-size: 0.85rem; }
  code { background: #f3f4f6; padding: 0.15em 0.4em; border-radius: 3px; font-size: 0.9em; }
  pre code { background: transparent; padding: 0; }
  table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; font-size: 0.875rem; }
  th, td { border: 1px solid #d1d5db; padding: 0.5rem 0.75rem; text-align: left; }
  th { background: #f9fafb; font-weight: 600; }
  blockquote { border-left: 3px solid #d1d5db; margin: 0.75rem 0; padding: 0.5rem 1rem; color: #6b7280; }
  ul, ol { padding-left: 1.5rem; }
  hr { border: none; border-top: 1px solid #e5e7eb; margin: 1.5rem 0; }
  @media print { body { margin: 0; padding: 20px; } }
</style></head><body>${html}</body></html>`);
                    win.document.close();
                    setTimeout(() => { win.print(); }, 250);
                  }}
                >
                  <FileDown className="mr-1 h-3.5 w-3.5" />
                  .pdf
                </Button>
              </div>
            </div>

            <TabsContent
              value="sections"
              className="flex flex-1 overflow-hidden mt-0"
            >
              <SectionSidebar
                sections={project.sections}
                activeSlug={activeSection?.section.slug}
                onSelect={handleSectionSelect}
                projectName={project.project.name}
                projectVersion={project.project.version}
                projectSlug={slug}
                onNavigateSettings={() => router.push(`/projects/${slug}/settings`)}
              />

              {sectionLoading ? (
                <LoadingOverlay />
              ) : activeSection ? (
                <SectionViewer
                  section={activeSection.section}
                  projectSlug={slug}
                  dependsOn={activeSection.depends_on}
                  dependedBy={activeSection.depended_by}
                  comments={activeSection.comments}
                  onCommentAdded={() => {
                    if (activeSection)
                      handleSectionSelect(activeSection.section.slug);
                    fetchProject(slug).then(setProject).catch(() => {});
                  }}
                  onTextSelected={handleSelectionContext}
                />
              ) : (
                <EmptyState
                  icon={FileText}
                  title="No sections"
                  description="This project has no sections yet."
                  className="flex-1"
                />
              )}
            </TabsContent>

            {/* Comments tab — all comments across project */}
            <TabsContent
              value="comments"
              className="flex-1 overflow-auto p-6 mt-0 bg-[var(--bg)]"
            >
              {allComments.length === 0 ? (
                <EmptyState
                  icon={MessageSquare}
                  title="No comments"
                  description="Select text in a section and add a comment to get started."
                />
              ) : (
                <div className="max-w-3xl mx-auto space-y-3">
                  {allComments.map((c) => (
                    <div
                      key={c.id}
                      className={`rounded-xl border border-[var(--border-color)] bg-[var(--card-bg)] p-4 transition-colors hover:border-[var(--accent)]/20 ${c.resolved ? "opacity-50" : ""}`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <button
                          className="text-xs font-medium text-primary hover:underline"
                          onClick={() => {
                            handleSectionSelect(c.section_slug);
                            setActiveTab("sections");
                          }}
                        >
                          {c.section_title}
                        </button>
                        <div className="flex items-center gap-2">
                          {c.resolved && (
                            <Badge variant="outline" className="text-xs">
                              Resolved
                            </Badge>
                          )}
                          <span className="text-xs text-muted-foreground">
                            {new Date(c.created_at).toLocaleString()}
                          </span>
                        </div>
                      </div>
                      <code className="text-xs bg-muted px-1.5 py-0.5 rounded block mb-2">
                        {c.anchor_text.length > 80
                          ? c.anchor_text.slice(0, 80) + "..."
                          : c.anchor_text}
                      </code>
                      <p className="text-sm">{c.body}</p>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent
              value="dependencies"
              className="flex-1 overflow-auto p-6 mt-0 bg-[var(--bg)]"
            >
              <DependencyGraph
                dependencies={project.dependencies}
                sections={project.sections}
                onSectionClick={(s) => { handleSectionSelect(s); setActiveTab("sections"); }}
              />
            </TabsContent>

            <TabsContent
              value="changelog"
              className="flex-1 overflow-auto p-6 mt-0 bg-[var(--bg)]"
            >
              {project.changelog.length === 0 ? (
                <EmptyState
                  icon={Clock}
                  title="No changelog entries"
                  description="Changes to sections will appear here."
                />
              ) : (
                <div className="max-w-3xl mx-auto space-y-3">
                  {project.changelog.map((entry, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 rounded-xl border border-[var(--border-color)] bg-[var(--card-bg)] p-4"
                    >
                      <div className="flex-1">
                        <p className="text-sm">
                          <span className="font-medium">
                            {entry.section_title}
                          </span>{" "}
                          <span className="text-muted-foreground">
                            rev {entry.revision_number}
                          </span>
                        </p>
                        {entry.change_description && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {entry.change_description}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(entry.created_at).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent
              value="stats"
              className="flex-1 overflow-auto p-6 mt-0 bg-[var(--bg)]"
            >
              {tokenStats ? (
                <div className="max-w-4xl mx-auto">
                  <TokenStatsDashboard stats={tokenStats} projectSlug={slug} />
                </div>
              ) : (
                <LoadingOverlay />
              )}
            </TabsContent>
          </Tabs>
        </div>

        {/* Chat panel */}
        {settings?.chat_enabled && (
          <ChatPanel
            projectSlug={slug}
            messages={chatMessages}
            onSend={handleChatSend}
            onStop={handleChatStop}
            onApprove={handleApprove}
            pendingApproval={pendingApproval}
            isStreaming={isStreaming}
            streamStatus={streamStatus}
            streamTools={streamTools}
            selectionContext={selectionContext}
            onClearSelection={() => setSelectionContext(null)}
          />
        )}
      </div>

      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-4xl h-[90vh] flex flex-col p-0">
          <DialogHeader className="px-6 py-4 border-b shrink-0">
            <div className="flex items-center justify-between pr-8">
              <DialogTitle>{project?.project.name} — Full PRD</DialogTitle>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const a = document.createElement("a");
                    a.href = `/api/projects/${slug}/export`;
                    a.download = `${slug}.md`;
                    a.click();
                  }}
                >
                  <Download className="mr-1.5 h-4 w-4" />
                  .md
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const printContent = document.getElementById("prd-print-area");
                    if (!printContent) return;
                    const win = window.open("", "_blank");
                    if (!win) return;
                    win.document.write(`<!DOCTYPE html>
<html><head><title>${project?.project.name ?? "PRD"}</title>
<style>
  *, *::before, *::after { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; line-height: 1.6; }
  h1 { font-size: 1.8rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.5rem; }
  h2 { font-size: 1.4rem; margin-top: 2rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.3rem; }
  h3 { font-size: 1.15rem; margin-top: 1.5rem; }
  pre { background: #f3f4f6; border-radius: 6px; padding: 1rem; overflow-x: auto; font-size: 0.85rem; }
  code { background: #f3f4f6; padding: 0.15em 0.4em; border-radius: 3px; font-size: 0.9em; }
  pre code { background: transparent; padding: 0; }
  table { width: 100%; border-collapse: collapse; margin: 0.75rem 0; font-size: 0.875rem; }
  th, td { border: 1px solid #d1d5db; padding: 0.5rem 0.75rem; text-align: left; }
  th { background: #f9fafb; font-weight: 600; }
  blockquote { border-left: 3px solid #d1d5db; margin: 0.75rem 0; padding: 0.5rem 1rem; color: #6b7280; }
  ul, ol { padding-left: 1.5rem; }
  hr { border: none; border-top: 1px solid #e5e7eb; margin: 1.5rem 0; }
  @media print { body { margin: 0; padding: 20px; } }
</style></head><body>${printContent.innerHTML}</body></html>`);
                    win.document.close();
                    setTimeout(() => { win.print(); }, 250);
                  }}
                >
                  <FileDown className="mr-1.5 h-4 w-4" />
                  .pdf
                </Button>
              </div>
            </div>
          </DialogHeader>
          <div id="prd-print-area" className="flex-1 overflow-y-auto px-8 py-6">
            <MarkdownRenderer content={previewContent} />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
