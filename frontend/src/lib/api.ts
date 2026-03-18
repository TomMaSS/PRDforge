import type {
  Project,
  ProjectDetail,
  ProjectSettings,
  Section,
  SectionDetail,
  TokenStats,
  ChangelogEntry,
  Revision,
  CreateProjectRequest,
  CreateSectionRequest,
  UpdateSectionRequest,
  Comment,
  Dependency,
} from "./types";

const API_BASE = "/api";

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

// Projects
export async function fetchProjects(): Promise<Project[]> {
  return apiFetch<Project[]>("/projects");
}

export async function fetchProject(slug: string): Promise<ProjectDetail> {
  return apiFetch<ProjectDetail>(`/projects/${slug}`);
}

export async function createProject(
  data: CreateProjectRequest
): Promise<Project> {
  return apiFetch<Project>("/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteProject(slug: string): Promise<void> {
  await apiFetch<void>(`/projects/${slug}`, { method: "DELETE" });
}

// Sections
export async function fetchSections(projectSlug: string): Promise<Section[]> {
  return apiFetch<Section[]>(`/projects/${projectSlug}/sections`);
}

export async function fetchSection(
  projectSlug: string,
  sectionSlug: string
): Promise<SectionDetail> {
  return apiFetch<SectionDetail>(
    `/projects/${projectSlug}/sections/${sectionSlug}`
  );
}

export async function createSection(
  projectSlug: string,
  data: CreateSectionRequest
): Promise<Section> {
  return apiFetch<Section>(`/projects/${projectSlug}/sections`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateSection(
  projectSlug: string,
  sectionSlug: string,
  data: UpdateSectionRequest
): Promise<Section> {
  return apiFetch<Section>(
    `/projects/${projectSlug}/sections/${sectionSlug}`,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    }
  );
}

export async function deleteSection(
  projectSlug: string,
  sectionSlug: string
): Promise<void> {
  await apiFetch<void>(
    `/projects/${projectSlug}/sections/${sectionSlug}`,
    { method: "DELETE" }
  );
}

// Settings
export async function fetchSettings(
  projectSlug: string
): Promise<ProjectSettings> {
  return apiFetch<ProjectSettings>(`/projects/${projectSlug}/settings`);
}

export async function updateSettings(
  projectSlug: string,
  data: Partial<ProjectSettings>
): Promise<ProjectSettings> {
  return apiFetch<ProjectSettings>(`/projects/${projectSlug}/settings`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// Token stats
export async function fetchTokenStats(
  projectSlug: string
): Promise<TokenStats> {
  return apiFetch<TokenStats>(`/projects/${projectSlug}/token-stats`);
}

// Changelog
export async function fetchChangelog(
  projectSlug: string
): Promise<ChangelogEntry[]> {
  return apiFetch<ChangelogEntry[]>(`/projects/${projectSlug}/changelog`);
}

// Revisions
export async function fetchRevisions(
  projectSlug: string,
  sectionSlug: string
): Promise<Revision[]> {
  return apiFetch<Revision[]>(
    `/projects/${projectSlug}/sections/${sectionSlug}/revisions`
  );
}

// Comments
export async function addComment(
  projectSlug: string,
  sectionSlug: string,
  content: string
): Promise<Comment> {
  return apiFetch<Comment>(
    `/projects/${projectSlug}/sections/${sectionSlug}/comments`,
    {
      method: "POST",
      body: JSON.stringify({ content }),
    }
  );
}

// Dependencies
export async function addDependency(
  projectSlug: string,
  fromSection: string,
  toSection: string,
  depType: string
): Promise<Dependency> {
  return apiFetch<Dependency>(`/projects/${projectSlug}/dependencies`, {
    method: "POST",
    body: JSON.stringify({
      from_section: fromSection,
      to_section: toSection,
      dep_type: depType,
    }),
  });
}

export async function removeDependency(
  projectSlug: string,
  fromSection: string,
  toSection: string
): Promise<void> {
  await apiFetch<void>(`/projects/${projectSlug}/dependencies`, {
    method: "DELETE",
    body: JSON.stringify({
      from_section: fromSection,
      to_section: toSection,
    }),
  });
}

// Markdown export/import
export async function exportMarkdown(projectSlug: string): Promise<string> {
  const res = await fetch(`${API_BASE}/projects/${projectSlug}/export`);
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  return res.text();
}

export async function importMarkdown(
  projectSlug: string,
  markdown: string
): Promise<void> {
  await apiFetch<void>(`/projects/${projectSlug}/import`, {
    method: "POST",
    body: JSON.stringify({ markdown }),
  });
}
