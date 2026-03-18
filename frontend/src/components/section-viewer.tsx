"use client";

import { Badge } from "@/components/ui/badge";
import { MarkdownRenderer } from "@/components/markdown-renderer";
import { StatusDot } from "@/components/status-dot";
import type { SectionDetail } from "@/lib/types";

interface SectionViewerProps {
  section: SectionDetail;
}

export function SectionViewer({ section }: SectionViewerProps) {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-bold">{section.title}</h1>
            <StatusDot status={section.status} showLabel />
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>{section.word_count} words</span>
            <span>
              {section.revision_count}{" "}
              {section.revision_count === 1 ? "revision" : "revisions"}
            </span>
            <span>
              Updated{" "}
              {new Date(section.updated_at).toLocaleDateString()}
            </span>
          </div>
        </div>

        {/* Dependencies */}
        {section.dependencies.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold mb-2 text-muted-foreground">
              Dependencies
            </h3>
            <div className="flex flex-wrap gap-2">
              {section.dependencies.map((dep) => (
                <Badge
                  key={`${dep.from_section}-${dep.to_section}`}
                  variant="secondary"
                >
                  {dep.to_section}{" "}
                  <span className="text-muted-foreground ml-1">
                    ({dep.dep_type})
                  </span>
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Content */}
        <MarkdownRenderer content={section.content} />

        {/* Comments */}
        {section.comments.length > 0 && (
          <div className="mt-8 border-t pt-6">
            <h3 className="text-sm font-semibold mb-4">
              Comments ({section.comments.length})
            </h3>
            <div className="space-y-4">
              {section.comments.map((comment) => (
                <div
                  key={comment.id}
                  className="rounded-lg border p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">
                      {comment.author}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(comment.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm">{comment.content}</p>
                  {comment.resolved && (
                    <Badge variant="outline" className="mt-2 text-xs">
                      Resolved
                    </Badge>
                  )}
                  {comment.replies.length > 0 && (
                    <div className="mt-3 space-y-2 pl-4 border-l-2">
                      {comment.replies.map((reply) => (
                        <div key={reply.id}>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-medium">
                              {reply.author}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {new Date(
                                reply.created_at
                              ).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-sm">{reply.content}</p>
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
