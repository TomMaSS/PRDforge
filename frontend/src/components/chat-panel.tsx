"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Loader2, X, ChevronDown, ChevronRight, Wrench, Brain, PenLine, Paperclip, Square, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MarkdownRenderer } from "@/components/markdown-renderer";
import { cn } from "@/lib/utils";
interface ChatMsg {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  created_at: string;
  context?: string;
  tools?: string[];
}

interface ChatAttachment {
  name: string;
  type: string;
  text_content: string;
}

interface ChatPanelProps {
  projectSlug: string;
  messages: ChatMsg[];
  onSend: (content: string, attachments?: ChatAttachment[]) => void;
  onStop?: () => void;
  onApprove?: (messageId: string) => void;
  pendingApproval?: { messageId: string; tools: string[] } | null;
  isStreaming?: boolean;
  streamStatus?: string;
  streamTools?: string[];
  selectionContext?: { selected_text: string; section_slug: string; section_title: string } | null;
  onClearSelection?: () => void;
}

export function ChatPanel({
  messages,
  onSend,
  onStop,
  onApprove,
  pendingApproval,
  isStreaming = false,
  streamStatus = "",
  streamTools = [],
  selectionContext,
  onClearSelection,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages or streaming updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed, attachments.length > 0 ? attachments : undefined);
    setInput("");
    setAttachments([]);
    onClearSelection?.();
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const newAttachments: ChatAttachment[] = [];
    for (const file of Array.from(files)) {
      if (file.size > 200_000) {
        continue; // Skip files > 200KB
      }
      const text = await file.text();
      newAttachments.push({
        name: file.name,
        type: file.type || "text/plain",
        text_content: text.slice(0, 12_000),
      });
    }
    setAttachments((prev) => [...prev, ...newAttachments]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex w-[40%] min-w-[480px] max-w-[700px] shrink-0 flex-col border-l border-[var(--border-color)] bg-[var(--surface)]">
      <div className="border-b border-[var(--border-color)] px-4 py-3">
        <h3 className="text-sm font-semibold">Chat</h3>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-8">
            Select text in a section to add context, then ask questions or request changes.
          </p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className="space-y-1">
            {/* Selection context shown above user message */}
            {msg.role === "user" && msg.context && (
              <div className="ml-6 rounded-md bg-primary/10 px-2.5 py-1.5 text-xs text-muted-foreground italic border border-primary/20">
                &ldquo;{msg.context.length > 100 ? msg.context.slice(0, 100) + "..." : msg.context}&rdquo;
              </div>
            )}
            <div
              className={cn(
                "rounded-xl px-3.5 py-2.5 text-sm",
                msg.role === "user"
                  ? "bg-[var(--accent)] text-white ml-8"
                  : "bg-[var(--card-bg)] border border-[var(--border-color)] mr-8"
              )}
            >
              {msg.role === "user" ? (
                msg.content
              ) : (
                <>
                  {msg.tools && msg.tools.length > 0 && (
                    <ToolCallsSummary tools={msg.tools} />
                  )}
                  <MarkdownRenderer content={msg.content} />
                </>
              )}
            </div>
          </div>
        ))}
        {isStreaming && (
          <StreamingIndicator status={streamStatus} tools={streamTools} />
        )}
        {pendingApproval && !isStreaming && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <ShieldCheck className="h-4 w-4 text-amber-500" />
              Tool approval needed
            </div>
            <p className="text-xs text-muted-foreground">
              The following tools need permission to run:
            </p>
            <div className="space-y-1">
              {pendingApproval.tools.map((tool, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs">
                  <Wrench className="h-3 w-3 text-muted-foreground" />
                  {prettifyToolName(tool)}
                </div>
              ))}
            </div>
            <Button
              size="sm"
              onClick={() => onApprove?.(pendingApproval.messageId)}
              className="w-full"
            >
              <ShieldCheck className="h-3.5 w-3.5 mr-1.5" />
              Approve and continue
            </Button>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Selection context */}
      {selectionContext && (
        <div className="border-t px-4 py-2 bg-primary/5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-primary">
              Context from: {selectionContext.section_title}
            </span>
            <button onClick={onClearSelection} className="text-muted-foreground hover:text-foreground">
              <X className="h-3 w-3" />
            </button>
          </div>
          <p className="text-xs text-muted-foreground line-clamp-2">
            &ldquo;{selectionContext.selected_text}&rdquo;
          </p>
        </div>
      )}

      {/* Attachments preview */}
      {attachments.length > 0 && (
        <div className="border-t px-4 py-2 flex flex-wrap gap-2">
          {attachments.map((att, i) => (
            <div key={i} className="flex items-center gap-1 rounded bg-muted px-2 py-1 text-xs">
              <Paperclip className="h-3 w-3" />
              <span className="max-w-[120px] truncate">{att.name}</span>
              <button onClick={() => setAttachments((prev) => prev.filter((_, j) => j !== i))}>
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="border-t border-[var(--border-color)] p-3 space-y-2 bg-[var(--card-bg)]">
        <Textarea
          placeholder="Type a message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          className="resize-none text-sm bg-[var(--surface-dim)] border-[var(--border-color)]"
        />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <Paperclip className="h-3.5 w-3.5" />
              Attach file
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".md,.txt,.json,.csv,.yml,.yaml,.toml,.xml,.html,.css,.js,.ts,.py,.go,.rs,.java,.rb,.sh,.sql,.doc,.docx"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
          <div className="flex items-center gap-2">
            {isStreaming ? (
              <Button
                variant="destructive"
                size="sm"
                onClick={onStop}
              >
                <Square className="h-3 w-3 mr-1.5 fill-current" />
                Stop
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={handleSubmit}
                disabled={!input.trim()}
              >
                <Send className="h-3.5 w-3.5 mr-1.5" />
                Send
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ToolCallsSummary({ tools }: { tools: string[] }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="mb-2 pb-2 border-b border-border/50">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
      >
        <Wrench className="h-3 w-3" />
        {tools.length} tool {tools.length === 1 ? "call" : "calls"}
        {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
      </button>
      {expanded && (
        <div className="mt-1 space-y-0.5 pl-4">
          {tools.map((tool, i) => (
            <div key={i} className="text-xs text-muted-foreground">
              {prettifyToolName(tool)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function prettifyToolName(name: string): string {
  return name
    .replace(/^mcp__prd-forge__/, "")
    .replace(/^mcp__/, "")
    .replace(/_/g, " ");
}

function StreamingIndicator({ status, tools }: { status: string; tools: string[] }) {
  const [expanded, setExpanded] = useState(false);

  const isToolUse = status.startsWith("Using:") || status === "tool_use";

  const statusIcon =
    status === "thinking" ? <Brain className="h-3.5 w-3.5 animate-pulse" /> :
    isToolUse ? <Wrench className="h-3.5 w-3.5 animate-spin" /> :
    status === "writing" ? <PenLine className="h-3.5 w-3.5" /> :
    status === "approval" ? <ShieldCheck className="h-3.5 w-3.5 text-amber-500" /> :
    <Loader2 className="h-3.5 w-3.5 animate-spin" />;

  const statusText =
    status === "thinking" ? "Thinking..." :
    status.startsWith("Using:") ? status :
    status === "tool_use" ? `Using: ${prettifyToolName(tools[tools.length - 1] || "")}` :
    status === "writing" ? "Writing..." :
    status === "approval" ? "Waiting for approval..." :
    "Processing...";

  return (
    <div className="rounded-lg border bg-card p-3 text-sm space-y-2">
      <div className="flex items-center gap-2 text-muted-foreground">
        {statusIcon}
        <span>{statusText}</span>
      </div>

      {tools.length > 0 && (
        <div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            {tools.length} tool {tools.length === 1 ? "call" : "calls"}
          </button>
          {expanded && (
            <div className="mt-1 space-y-1 pl-4">
              {tools.map((tool, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Wrench className="h-2.5 w-2.5 shrink-0" />
                  <span>{prettifyToolName(tool)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
