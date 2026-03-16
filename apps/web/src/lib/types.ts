export type Project = {
  id: string;
  name: string;
  source_type: string | null;
  source_url: string | null;
  default_branch: string | null;
  status: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  last_indexed_at: string | null;
};

export type IndexJob = {
  id: string;
  project_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  summary: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
};

export type ProjectDetail = Project & {
  file_count: number;
  chunk_count: number;
  latest_job: IndexJob | null;
};

export type RepositoryFile = {
  id: string;
  project_id: string;
  path: string;
  language: string | null;
  file_size: number;
  checksum: string;
  is_supported: boolean;
  summary: string | null;
  created_at: string;
};

export type CodeChunk = {
  id: string;
  repository_file_id: string;
  path: string;
  language: string | null;
  chunk_index: number;
  chunk_type: string;
  symbol_name: string | null;
  start_line: number | null;
  end_line: number | null;
  content: string;
  chunk_metadata: Record<string, unknown>;
  created_at: string;
};

export type RepositoryFileDetail = RepositoryFile & {
  content_text: string | null;
  chunks: CodeChunk[];
};

export type ChatSession = {
  id: string;
  project_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export type Citation = {
  chunk_id: string;
  file_id: string;
  path: string;
  chunk_type: string;
  symbol_name: string | null;
  start_line: number | null;
  end_line: number | null;
  preview: string;
};

export type ChatMessage = {
  id: string;
  chat_session_id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  created_at: string;
};

export type ChatReply = {
  session: ChatSession;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  suggested_follow_ups: string[];
};

