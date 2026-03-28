"use client";

import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import "highlight.js/styles/github-dark.min.css";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

const mdComponents: Components = {
  h1: ({ children }) => (
    <h1 className="text-xl font-bold text-[var(--md-heading)] mt-8 mb-4 first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-lg font-semibold text-[var(--md-heading)] mt-8 mb-3 border-l-2 border-[var(--accent)]/40 pl-3">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-base font-semibold text-[var(--md-heading-sub)] mt-6 mb-2">
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p className="text-[var(--md-body)] mb-4 leading-relaxed">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="text-[var(--md-bold)] font-semibold">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-[var(--md-body)]">{children}</em>
  ),
  a: ({ href, children }) => (
    <a href={href} className="text-[var(--accent-light)] underline underline-offset-2 hover:text-[var(--accent)] transition-colors">
      {children}
    </a>
  ),

  // Lists
  ul: ({ children }) => (
    <ul className="space-y-2 my-4 pl-0 list-none">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="space-y-2 my-4 list-decimal list-inside marker:text-[var(--md-muted)] marker:font-mono marker:tabular-nums">
      {children}
    </ol>
  ),
  li: ({ children }) => (
    <li className="text-[var(--md-body)] flex items-start gap-2">
      <span className="text-[var(--accent-light)] mt-[0.45rem] text-[0.5rem] shrink-0">●</span>
      <span className="flex-1">{children}</span>
    </li>
  ),

  // Tables
  table: ({ children }) => (
    <div className="rounded-lg border border-white/[0.08] overflow-hidden my-6">
      <table className="w-full border-collapse">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-white/[0.06]">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="px-4 py-2.5 text-left text-[0.6875rem] text-[var(--md-muted)] uppercase tracking-wider font-medium border-b border-white/[0.1]">
      {children}
    </th>
  ),
  tbody: ({ children }) => (
    <tbody className="divide-y divide-white/[0.05]">{children}</tbody>
  ),
  tr: ({ children }) => (
    <tr className="even:bg-white/[0.02] hover:bg-white/[0.04] transition-colors duration-75">
      {children}
    </tr>
  ),
  td: ({ children }) => (
    <td className="px-4 py-3 text-sm text-[var(--md-body)]">{children}</td>
  ),

  // Blockquotes
  blockquote: ({ children }) => (
    <blockquote className="border-l-3 border-white/[0.15] pl-4 my-4 italic text-[var(--md-muted)]">
      {children}
    </blockquote>
  ),

  // Code — inline (not inside pre)
  code: ({ className, children, ...props }) => {
    const isBlock = className?.includes("hljs") || className?.includes("language-");
    if (isBlock) {
      return <code className={cn(className, "text-sm leading-relaxed")} {...props}>{children}</code>;
    }
    return (
      <code className="bg-white/[0.06] px-1.5 py-0.5 rounded text-[0.8125rem] font-mono text-[var(--md-code)] border border-white/[0.06]">
        {children}
      </code>
    );
  },

  // Code blocks
  pre: ({ children }) => (
    <pre className="bg-[var(--code-bg)] rounded-lg p-4 border border-[var(--code-border)] my-4 overflow-x-auto">
      {children}
    </pre>
  ),

  // Horizontal rule
  hr: () => (
    <hr className="border-none border-t border-white/[0.08] my-8" />
  ),

  // Images
  img: ({ src, alt }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt || ""} className="max-w-full rounded-lg my-4" />
  ),
};

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn("markdown-body", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true }]]}
        components={mdComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
