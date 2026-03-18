import type {
  Project,
  ProjectDetailResponse,
  SectionDetailResponse,
  TokenStats,
} from "./types";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error?.message ?? body.error ?? res.statusText);
  }
  return res.json();
}

export async function fetchProjects(): Promise<Project[]> {
  return apiFetch<Project[]>("/api/projects");
}

export async function fetchProject(slug: string): Promise<ProjectDetailResponse> {
  return apiFetch<ProjectDetailResponse>(`/api/projects/${slug}`);
}

export async function fetchSection(
  projectSlug: string,
  sectionSlug: string
): Promise<SectionDetailResponse> {
  return apiFetch<SectionDetailResponse>(
    `/api/projects/${projectSlug}/sections/${sectionSlug}`
  );
}

export async function fetchTokenStats(slug: string): Promise<TokenStats> {
  return apiFetch<TokenStats>(`/api/projects/${slug}/token-stats`);
}

export async function createProject(data: {
  name: string;
  description?: string;
}): Promise<Project> {
  return apiFetch<Project>("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
