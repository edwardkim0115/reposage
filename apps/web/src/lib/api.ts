import {
  ChatMessage,
  ChatReply,
  ChatSession,
  CodeChunk,
  IndexJob,
  Project,
  ProjectDetail,
  RepositoryFile,
  RepositoryFileDetail
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store"
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed." }));
    throw new Error(payload.detail ?? "Request failed.");
  }

  return (await response.json()) as T;
}

export const api = {
  listProjects: () => request<Project[]>("/projects"),
  createProject: (name: string) =>
    request<Project>("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name })
    }),
  createGithubProject: (payload: { name: string; source_url: string }) =>
    request<ProjectDetail>("/projects/github", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }),
  uploadZipProject: (name: string, file: File) => {
    const formData = new FormData();
    formData.append("name", name);
    formData.append("file", file);
    return request<ProjectDetail>("/projects/upload-zip", {
      method: "POST",
      body: formData
    });
  },
  getProject: (projectId: string) => request<ProjectDetail>(`/projects/${projectId}`),
  reindexProject: (projectId: string) =>
    request<IndexJob>(`/projects/${projectId}/reindex`, { method: "POST" }),
  listFiles: (projectId: string, search?: string) =>
    request<RepositoryFile[]>(
      `/projects/${projectId}/files${search ? `?search=${encodeURIComponent(search)}` : ""}`
    ),
  getFile: (projectId: string, fileId: string) =>
    request<RepositoryFileDetail>(`/projects/${projectId}/files/${fileId}`),
  listChunks: (projectId: string, fileId?: string) =>
    request<CodeChunk[]>(
      `/projects/${projectId}/chunks${fileId ? `?file_id=${encodeURIComponent(fileId)}` : ""}`
    ),
  listJobs: (projectId: string) => request<IndexJob[]>(`/projects/${projectId}/jobs`),
  listChatSessions: (projectId: string) =>
    request<ChatSession[]>(`/projects/${projectId}/chat/sessions`),
  createChatSession: (projectId: string, title?: string) =>
    request<ChatSession>(`/projects/${projectId}/chat/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: title ?? null })
    }),
  listMessages: (chatSessionId: string) =>
    request<ChatMessage[]>(`/chat/sessions/${chatSessionId}/messages`),
  postMessage: (chatSessionId: string, content: string) =>
    request<ChatReply>(`/chat/sessions/${chatSessionId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    })
};

