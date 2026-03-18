export interface Project {
  slug: string;
  name: string;
  description: string;
  section_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail extends Project {
  sections: Section[];
  settings: ProjectSettings;
}

export interface ProjectSettings {
  comment_replies_enabled: boolean;
  chat_enabled: boolean;
  llm_provider: string;
  llm_model: string;
}

export interface Section {
  slug: string;
  title: string;
  status: SectionStatus;
  order_index: number;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export type SectionStatus =
  | "draft"
  | "in_progress"
  | "review"
  | "approved"
  | "outdated";

export interface SectionDetail extends Section {
  content: string;
  comments: Comment[];
  dependencies: Dependency[];
  revision_count: number;
}

export interface Comment {
  id: string;
  author: string;
  content: string;
  resolved: boolean;
  created_at: string;
  replies: CommentReply[];
}

export interface CommentReply {
  id: string;
  author: string;
  content: string;
  created_at: string;
}

export interface Dependency {
  from_section: string;
  to_section: string;
  dep_type: string;
}

export interface Revision {
  id: string;
  section_slug: string;
  version: number;
  diff_summary: string;
  created_at: string;
}

export interface ChangelogEntry {
  id: string;
  action: string;
  target: string;
  detail: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface TokenStats {
  total_operations: number;
  total_tokens_saved: number;
  savings_percentage: number;
  by_operation: OperationStats[];
  daily_trend: DailyTrend[];
  activity: TokenActivity[];
  project_stats: ProjectTokenStats;
}

export interface OperationStats {
  operation: string;
  count: number;
  tokens_saved: number;
  avg_savings: number;
}

export interface DailyTrend {
  date: string;
  tokens_saved: number;
  operations: number;
}

export interface TokenActivity {
  operation: string;
  section: string;
  tokens_saved: number;
  timestamp: string;
}

export interface ProjectTokenStats {
  total_sections: number;
  total_tokens: number;
  avg_tokens_per_section: number;
}

export interface CreateProjectRequest {
  name: string;
  description: string;
}

export interface UpdateSectionRequest {
  content?: string;
  status?: SectionStatus;
  title?: string;
}

export interface CreateSectionRequest {
  title: string;
  content?: string;
}
