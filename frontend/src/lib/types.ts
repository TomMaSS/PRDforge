export type SectionStatus =
  | "draft"
  | "in_progress"
  | "review"
  | "approved"
  | "outdated";

export interface Project {
  slug: string;
  name: string;
  description: string;
  version: number;
  section_count: number;
  total_words: number;
  created_at: string;
  updated_at: string;
}

export interface SectionListItem {
  slug: string;
  title: string;
  section_type: string;
  sort_order: number;
  status: SectionStatus;
  summary: string;
  tags: string[];
  word_count: number;
  parent_slug: string | null;
  revision_count: number;
  updated_at: string;
}

export interface ProjectDetailResponse {
  project: {
    slug: string;
    name: string;
    description: string;
    version: number;
    created_at: string;
  };
  stats: {
    sections: number;
    words: number;
    by_status: Record<string, number>;
  };
  sections: SectionListItem[];
  dependencies: {
    from_slug: string;
    to_slug: string;
    type: string;
    description: string;
  }[];
  changelog: {
    section_slug: string;
    section_title: string;
    revision_number: number;
    change_description: string;
    created_at: string;
  }[];
}

export interface SectionDetailResponse {
  section: {
    slug: string;
    title: string;
    content: string;
    summary: string;
    status: SectionStatus;
    section_type: string;
    tags: string[];
    notes: string;
    word_count: number;
    updated_at: string;
  };
  depends_on: { slug: string; title: string; summary: string; dependency_type: string }[];
  depended_by: { slug: string; title: string; summary: string; dependency_type: string }[];
  revisions: { revision_number: number; change_description: string; created_at: string }[];
  comments: {
    id: string;
    anchor_text: string;
    body: string;
    resolved: boolean;
    created_at: string;
    replies: { id: string; author: string; body: string; created_at: string }[];
  }[];
}

export interface TokenStats {
  operations: number;
  total_full_doc_tokens: number;
  total_loaded_tokens: number;
  total_saved_tokens: number;
  savings_percent: number;
  by_operation: {
    operation: string;
    count: number;
    full_tokens: number;
    loaded_tokens: number;
  }[];
  daily_trend: {
    day: string;
    operations: number;
    tokens_saved: number;
  }[];
  project_stats: {
    sections: number;
    dependencies: number;
    revisions: number;
  };
  activity: {
    tool_name: string;
    detail: Record<string, unknown>;
    created_at: string;
  }[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ProjectSettings {
  claude_comment_replies: boolean;
  chat_enabled: boolean;
  chat_provider: "claude_cli" | "anthropic_api";
  chat_model: "sonnet" | "opus" | "haiku";
}
