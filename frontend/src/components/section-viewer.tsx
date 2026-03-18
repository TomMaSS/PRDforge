"use client";

import { useState, useCallback, useRef } from "react";
import { MessageSquarePlus, Pencil, Trash2, Check, X } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MarkdownRenderer } from "@/components/markdown-renderer";
import { StatusDot } from "@/components/status-dot";
import type { SectionDetailResponse } from "@/lib/types";

interface SectionViewerProps {
  section: SectionDetailResponse["section"];
  projectSlug: string;
  dependsOn?: SectionDetailResponse["depends_on"];
  dependedBy?: SectionDetailResponse["depended_by"];
  comments?: SectionDetailResponse["comments"];
  onCommentAdded?: () => void;
  onTextSelected?: (text: string) => void;
}

export function SectionViewer({
  section,
  projectSlug,
  dependsOn = [],
  dependedBy = [],
  comments = [],
  onCommentAdded,
  onTextSelected,
}: SectionViewerProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [selectedText, setSelectedText] = useState("");
  const [selectionAnchor, setSelectionAnchor] = useState<{
    anchor_text: string;
    anchor_prefix: string;
    anchor_suffix: string;
  } | null>(null);
  const [commentBody, setCommentBody] = useState("");
  const [showCommentForm, setShowCommentForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");

  const handleStatusChange = async (newStatus: string) => {
    try {
      const res = await fetch(
        `/api/projects/${projectSlug}/sections/${section.slug}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: newStatus }),
        }
      );
      if (!res.ok) throw new Error("Failed to update status");
      toast.success(`Status changed to ${newStatus.replace("_", " ")}`);
      onCommentAdded?.(); // triggers section reload
    } catch {
      toast.error("Failed to update status");
    }
  };

  const handleTextSelect = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !contentRef.current) return;

    const text = sel.toString().trim();
    if (!text || text.length < 3) return;

    // Check if selected text already has an unresolved comment
    const existingComment = comments.find(
      (c) => !c.resolved && text.includes(c.anchor_text)
    ) || comments.find(
      (c) => !c.resolved && c.anchor_text.includes(text)
    );

    if (existingComment) {
      // Scroll to existing comment instead of creating new one
      const el = document.getElementById(`comment-${existingComment.id}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("ring-2", "ring-primary");
        setTimeout(() => el.classList.remove("ring-2", "ring-primary"), 2000);
      }
      setShowCommentForm(false);
      onTextSelected?.(text);
      return;
    }

    const fullContent = section.content;
    const idx = fullContent.indexOf(text);
    if (idx === -1) {
      setSelectedText(text);
      setSelectionAnchor({ anchor_text: text, anchor_prefix: "", anchor_suffix: "" });
    } else {
      const prefixStart = Math.max(0, idx - 40);
      const suffixEnd = Math.min(fullContent.length, idx + text.length + 40);
      setSelectedText(text);
      setSelectionAnchor({
        anchor_text: text,
        anchor_prefix: fullContent.slice(prefixStart, idx),
        anchor_suffix: fullContent.slice(idx + text.length, suffixEnd),
      });
    }
    setShowCommentForm(true);
    onTextSelected?.(text);
  }, [section.content, comments, onTextSelected]);

  const handleAddComment = async () => {
    if (!selectionAnchor || !commentBody.trim()) return;
    setSubmitting(true);
    try {
      const res = await fetch(
        `/api/projects/${projectSlug}/sections/${section.slug}/comments`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            anchor_text: selectionAnchor.anchor_text,
            anchor_prefix: selectionAnchor.anchor_prefix,
            anchor_suffix: selectionAnchor.anchor_suffix,
            body: commentBody.trim(),
          }),
        }
      );
      if (!res.ok) throw new Error("Failed to add comment");
      toast.success("Comment added");
      setShowCommentForm(false);
      setCommentBody("");
      setSelectedText("");
      setSelectionAnchor(null);
      onCommentAdded?.();
    } catch {
      toast.error("Failed to add comment");
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleResolve = async (commentId: string, currentlyResolved: boolean) => {
    try {
      await fetch(
        `/api/projects/${projectSlug}/sections/${section.slug}/comments/${commentId}/resolve`,
        { method: "POST" }
      );
      toast.success(currentlyResolved ? "Comment reopened" : "Comment resolved");
      onCommentAdded?.();
    } catch {
      toast.error("Failed to update comment");
    }
  };

  const handleDelete = async (commentId: string) => {
    if (!confirm("Delete this comment?")) return;
    try {
      await fetch(
        `/api/projects/${projectSlug}/sections/${section.slug}/comments/${commentId}`,
        { method: "DELETE" }
      );
      toast.success("Comment deleted");
      onCommentAdded?.();
    } catch {
      toast.error("Failed to delete comment");
    }
  };

  const handleEditSave = async (commentId: string) => {
    if (!editBody.trim()) return;
    try {
      await fetch(
        `/api/projects/${projectSlug}/sections/${section.slug}/comments/${commentId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ body: editBody.trim() }),
        }
      );
      toast.success("Comment updated");
      setEditingId(null);
      setEditBody("");
      onCommentAdded?.();
    } catch {
      toast.error("Failed to update comment");
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold">{section.title}</h1>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium hover:bg-secondary transition-colors cursor-pointer border border-transparent hover:border-border">
                  <StatusDot status={section.status} showLabel />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                {(["draft", "in_progress", "review", "approved", "outdated"] as const).map((s) => (
                  <DropdownMenuItem
                    key={s}
                    onClick={() => handleStatusChange(s)}
                    className={section.status === s ? "font-semibold" : ""}
                  >
                    <StatusDot status={s} showLabel />
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>{section.word_count} words</span>
            <Badge variant="outline" className="text-xs">
              {section.section_type}
            </Badge>
            <span>
              Updated {new Date(section.updated_at).toLocaleDateString()}
            </span>
          </div>
        </div>

        {/* Dependencies */}
        {dependsOn.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold mb-2 text-muted-foreground">Depends on</h3>
            <div className="flex flex-wrap gap-2">
              {dependsOn.map((dep) => (
                <Badge key={dep.slug} variant="secondary">
                  {dep.title}
                  <span className="text-muted-foreground ml-1">({dep.dependency_type})</span>
                </Badge>
              ))}
            </div>
          </div>
        )}

        {dependedBy.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold mb-2 text-muted-foreground">Depended by</h3>
            <div className="flex flex-wrap gap-2">
              {dependedBy.map((dep) => (
                <Badge key={dep.slug} variant="secondary">{dep.title}</Badge>
              ))}
            </div>
          </div>
        )}

        {/* Inline comment form */}
        {showCommentForm && selectedText && (
          <div className="mb-4 rounded-lg border border-primary/30 bg-primary/5 p-4">
            <div className="flex items-center gap-2 mb-2">
              <MessageSquarePlus className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">Add comment on selected text</span>
              <button
                onClick={() => { setShowCommentForm(false); setSelectedText(""); }}
                className="ml-auto text-xs text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
            </div>
            <div className="mb-2 rounded bg-card p-2">
              <code className="text-xs text-muted-foreground">
                &ldquo;{selectedText.length > 80 ? selectedText.slice(0, 80) + "..." : selectedText}&rdquo;
              </code>
            </div>
            <Textarea
              placeholder="Your comment..."
              value={commentBody}
              onChange={(e) => setCommentBody(e.target.value)}
              rows={2}
              className="mb-2"
            />
            <Button size="sm" onClick={handleAddComment} disabled={!commentBody.trim() || submitting}>
              {submitting ? "Adding..." : "Add Comment"}
            </Button>
          </div>
        )}

        {/* Content */}
        <div ref={contentRef} onMouseUp={handleTextSelect}>
          <MarkdownRenderer content={section.content} />
        </div>

        {/* Notes */}
        {section.notes && (
          <div className="mt-6 rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
            <h3 className="text-sm font-semibold mb-2">Notes</h3>
            <MarkdownRenderer content={section.notes} className="text-sm" />
          </div>
        )}

        {/* Comments panel */}
        {comments.length > 0 && (
          <div className="mt-8 border-t pt-6">
            <h3 className="text-sm font-semibold mb-4">
              Comments ({comments.length})
            </h3>
            <div className="space-y-4">
              {comments.map((comment) => (
                <div
                  key={comment.id}
                  id={`comment-${comment.id}`}
                  className={`rounded-lg border p-4 transition-all ${comment.resolved ? "opacity-50" : ""}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                      {comment.anchor_text.length > 60
                        ? comment.anchor_text.slice(0, 60) + "..."
                        : comment.anchor_text}
                    </code>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs h-6 px-2"
                        onClick={() => handleToggleResolve(comment.id, comment.resolved)}
                      >
                        {comment.resolved ? "Reopen" : "Resolve"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => {
                          setEditingId(comment.id);
                          setEditBody(comment.body);
                        }}
                      >
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-destructive"
                        onClick={() => handleDelete(comment.id)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                      <span className="text-xs text-muted-foreground ml-1">
                        {new Date(comment.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  {editingId === comment.id ? (
                    <div className="space-y-2">
                      <Textarea
                        value={editBody}
                        onChange={(e) => setEditBody(e.target.value)}
                        rows={2}
                        className="text-sm"
                      />
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => handleEditSave(comment.id)} disabled={!editBody.trim()}>
                          <Check className="h-3 w-3 mr-1" /> Save
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                          <X className="h-3 w-3 mr-1" /> Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm">{comment.body}</p>
                  )}

                  {comment.replies && comment.replies.length > 0 && (
                    <div className="mt-3 space-y-2 pl-4 border-l-2">
                      {comment.replies.map((reply) => (
                        <div key={reply.id}>
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className="text-xs">{reply.author}</Badge>
                            <span className="text-xs text-muted-foreground">
                              {new Date(reply.created_at).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-sm">{reply.body}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
