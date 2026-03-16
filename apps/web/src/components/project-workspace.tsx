"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, FileCode2, RefreshCw, SendHorizonal } from "lucide-react";
import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { Citation } from "@/lib/types";
import { formatDate } from "@/lib/utils";

export function ProjectWorkspace({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [fileSearch, setFileSearch] = useState("");
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [highlightedCitation, setHighlightedCitation] = useState<Citation | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
    refetchInterval: (query) =>
      query.state.data?.status === "queued" || query.state.data?.status === "indexing" ? 4000 : false
  });

  const filesQuery = useQuery({
    queryKey: ["files", projectId, fileSearch],
    queryFn: () => api.listFiles(projectId, fileSearch)
  });

  const jobsQuery = useQuery({
    queryKey: ["jobs", projectId],
    queryFn: () => api.listJobs(projectId),
    refetchInterval: projectQuery.data?.status === "ready" ? false : 4000
  });

  const sessionsQuery = useQuery({
    queryKey: ["chat-sessions", projectId],
    queryFn: () => api.listChatSessions(projectId)
  });

  const fileDetailQuery = useQuery({
    queryKey: ["file", projectId, selectedFileId],
    queryFn: () => api.getFile(projectId, selectedFileId as string),
    enabled: Boolean(selectedFileId)
  });

  const messagesQuery = useQuery({
    queryKey: ["messages", activeSessionId],
    queryFn: () => api.listMessages(activeSessionId as string),
    enabled: Boolean(activeSessionId)
  });

  const createSessionMutation = useMutation({
    mutationFn: () => api.createChatSession(projectId),
    onSuccess: async (session) => {
      setActiveSessionId(session.id);
      await queryClient.invalidateQueries({ queryKey: ["chat-sessions", projectId] });
    }
  });

  const reindexMutation = useMutation({
    mutationFn: () => api.reindexProject(projectId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      await queryClient.invalidateQueries({ queryKey: ["jobs", projectId] });
    }
  });

  const sendMessageMutation = useMutation({
    mutationFn: () => api.postMessage(activeSessionId as string, question),
    onSuccess: async () => {
      setQuestion("");
      setChatError(null);
      await queryClient.invalidateQueries({ queryKey: ["messages", activeSessionId] });
    },
    onError: (error: Error) => setChatError(error.message)
  });

  useEffect(() => {
    if (!filesQuery.data?.length || selectedFileId) return;
    setSelectedFileId(filesQuery.data[0].id);
  }, [filesQuery.data, selectedFileId]);

  useEffect(() => {
    if (!sessionsQuery.data) return;
    if (!activeSessionId && sessionsQuery.data.length === 0 && !createSessionMutation.isPending) {
      createSessionMutation.mutate();
      return;
    }
    if (!activeSessionId && sessionsQuery.data.length > 0) {
      setActiveSessionId(sessionsQuery.data[0].id);
    }
  }, [activeSessionId, createSessionMutation, sessionsQuery.data]);

  useEffect(() => {
    if (!highlightedCitation || fileDetailQuery.data?.id !== highlightedCitation.file_id) return;
    const targetLine = highlightedCitation.start_line ?? highlightedCitation.end_line;
    if (!targetLine) return;
    const element = document.querySelector(`[data-line="${targetLine}"]`);
    element?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [fileDetailQuery.data, highlightedCitation]);

  const selectedRange = highlightedCitation
    ? {
        start: highlightedCitation.start_line ?? highlightedCitation.end_line ?? 0,
        end: highlightedCitation.end_line ?? highlightedCitation.start_line ?? 0
      }
    : null;

  const sourceLines = (fileDetailQuery.data?.content_text ?? "").split("\n");

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-[1700px] flex-col gap-6 px-4 py-6 sm:px-6 xl:px-8">
      <header className="grid gap-4 xl:grid-cols-[1.4fr_0.6fr]">
        <Panel className="bg-[radial-gradient(circle_at_top_left,rgba(232,182,93,0.16),transparent_40%),linear-gradient(180deg,rgba(16,31,53,0.96),rgba(9,19,33,0.98))]">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-3">
              <p className="font-mono text-xs uppercase tracking-[0.22em] text-mist/55">
                Repository Workspace
              </p>
              <h1 className="text-3xl font-semibold text-white sm:text-4xl">
                {projectQuery.data?.name ?? "Loading project"}
              </h1>
              <p className="max-w-3xl text-sm leading-7 text-mist/66">
                {projectQuery.data?.source_url ??
                  "This project was created without a source. Attach one before indexing."}
              </p>
              <div className="flex flex-wrap items-center gap-3 text-sm text-mist/55">
                <StatusBadge status={projectQuery.data?.status ?? "created"} />
                <span>Files: {projectQuery.data?.file_count ?? 0}</span>
                <span>Chunks: {projectQuery.data?.chunk_count ?? 0}</span>
                <span>Last indexed: {formatDate(projectQuery.data?.last_indexed_at)}</span>
              </div>
            </div>
            <Button
              variant="secondary"
              onClick={() => reindexMutation.mutate()}
              disabled={reindexMutation.isPending || !projectQuery.data?.source_type}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Re-index project
            </Button>
          </div>
        </Panel>

        <Panel>
          <div className="space-y-3">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-mist/55">Latest Job</p>
            <div className="flex items-center justify-between">
              <StatusBadge status={projectQuery.data?.latest_job?.status ?? "created"} />
              <span className="text-sm text-mist/60">
                {formatDate(projectQuery.data?.latest_job?.created_at)}
              </span>
            </div>
            <div className="space-y-1 text-sm text-mist/62">
              <p>
                Stage: {(projectQuery.data?.latest_job?.summary?.stage as string | undefined) ?? "n/a"}
              </p>
              <p>
                Files indexed:{" "}
                {(projectQuery.data?.latest_job?.summary?.files_indexed as number | undefined) ?? 0}
              </p>
              <p>
                Chunks created:{" "}
                {(projectQuery.data?.latest_job?.summary?.chunks_created as number | undefined) ?? 0}
              </p>
            </div>
            {projectQuery.data?.error_message ? (
              <div className="rounded-2xl border border-rose/30 bg-rose/10 p-3 text-sm text-rose">
                {projectQuery.data.error_message}
              </div>
            ) : null}
          </div>
        </Panel>
      </header>

      <div className="grid gap-6 xl:grid-cols-[330px_minmax(0,1fr)]">
        <div className="space-y-6">
          <Panel className="p-4">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-mist/55">Files</p>
                <h2 className="mt-2 text-xl font-semibold text-white">Indexed source</h2>
              </div>
              <FileCode2 className="h-5 w-5 text-accent" />
            </div>
            <Input
              value={fileSearch}
              onChange={(event) => setFileSearch(event.target.value)}
              placeholder="Search file paths"
              className="mb-4"
            />
            <div className="max-h-[620px] space-y-2 overflow-auto pr-1">
              {filesQuery.data?.map((file) => (
                <button
                  key={file.id}
                  type="button"
                  onClick={() => {
                    setSelectedFileId(file.id);
                    setHighlightedCitation(null);
                  }}
                  className={`w-full rounded-2xl border px-3 py-3 text-left transition ${
                    selectedFileId === file.id
                      ? "border-accent bg-accent/10"
                      : "border-white/8 bg-white/5 hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="break-words text-sm text-mist">{file.path}</span>
                    <span className="font-mono text-[11px] uppercase tracking-[0.16em] text-mist/40">
                      {file.language ?? "n/a"}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-mist/48">
                    {file.summary ?? "Unsupported or skipped file."}
                  </p>
                </button>
              ))}
            </div>
          </Panel>

          <Panel className="p-4">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-mist/55">Job History</p>
            <div className="mt-4 space-y-3">
              {jobsQuery.data?.map((job) => (
                <div key={job.id} className="rounded-2xl border border-white/8 bg-white/5 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <StatusBadge status={job.status} />
                    <span className="text-xs text-mist/55">{formatDate(job.created_at)}</span>
                  </div>
                  <p className="mt-2 text-sm text-mist/60">
                    Stage: {(job.summary?.stage as string | undefined) ?? "n/a"}
                  </p>
                  {job.error_message ? (
                    <p className="mt-2 text-sm text-rose">{job.error_message}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </Panel>
        </div>

        <div className="grid gap-6 xl:grid-rows-[0.95fr_1.05fr]">
          <Panel className="flex min-h-[420px] flex-col">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-mist/55">Chat</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">
                  Grounded repository answers
                </h2>
              </div>
              {projectQuery.data?.status !== "ready" ? (
                <div className="flex items-center gap-2 rounded-full border border-amber/30 bg-amber/10 px-3 py-2 text-xs text-amber">
                  <AlertTriangle className="h-4 w-4" />
                  Indexing still in progress
                </div>
              ) : null}
            </div>

            <div className="flex-1 space-y-4 overflow-auto pr-1">
              {messagesQuery.data?.map((message) => (
                <div
                  key={message.id}
                  className={`rounded-[26px] border p-4 ${
                    message.role === "assistant"
                      ? "border-white/8 bg-white/5"
                      : "border-accent/25 bg-accent/10"
                  }`}
                >
                  <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.16em] text-mist/45">
                    <span>{message.role}</span>
                    <span>{formatDate(message.created_at)}</span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm leading-7 text-mist">{message.content}</p>
                  {message.citations?.length ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {message.citations.map((citation) => (
                        <button
                          key={citation.chunk_id}
                          type="button"
                          onClick={() => {
                            setSelectedFileId(citation.file_id);
                            setHighlightedCitation(citation);
                          }}
                          className="rounded-2xl border border-white/10 bg-[#091525] px-3 py-2 text-left text-xs text-mist/78 transition hover:border-accent"
                        >
                          <div className="font-mono text-[11px] uppercase tracking-[0.15em] text-accent">
                            {citation.chunk_type}
                          </div>
                          <div className="mt-1 text-mist">{citation.path}</div>
                          {citation.start_line ? (
                            <div className="mt-1 text-mist/45">
                              lines {citation.start_line}-{citation.end_line ?? citation.start_line}
                            </div>
                          ) : null}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>

            {chatError ? (
              <div className="mt-4 rounded-2xl border border-rose/30 bg-rose/10 px-4 py-3 text-sm text-rose">
                {chatError}
              </div>
            ) : null}

            <div className="mt-4 space-y-3 border-t border-white/8 pt-4">
              <Textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Where is authentication handled?"
              />
              <div className="flex justify-end">
                <Button
                  onClick={() => sendMessageMutation.mutate()}
                  disabled={!activeSessionId || !question.trim() || sendMessageMutation.isPending}
                >
                  <SendHorizonal className="mr-2 h-4 w-4" />
                  Ask RepoSage
                </Button>
              </div>
            </div>
          </Panel>

          <Panel className="min-h-[420px] overflow-hidden">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-mist/55">
                  Source Preview
                </p>
                <h2 className="mt-2 text-2xl font-semibold text-white">
                  {fileDetailQuery.data?.path ?? "Select a file"}
                </h2>
              </div>
              <div className="text-right text-sm text-mist/55">
                <p>{fileDetailQuery.data?.language ?? "n/a"}</p>
                {highlightedCitation?.start_line ? (
                  <p>
                    Focus lines {highlightedCitation.start_line}-
                    {highlightedCitation.end_line ?? highlightedCitation.start_line}
                  </p>
                ) : null}
              </div>
            </div>
            <div className="grid gap-4 xl:grid-cols-[1fr_280px]">
              <div className="max-h-[520px] overflow-auto rounded-[26px] border border-white/8 bg-[#08111f] p-4">
                {sourceLines.length > 0 ? (
                  <pre className="text-sm leading-6 text-mist/88">
                    {sourceLines.map((line, index) => {
                      const lineNumber = index + 1;
                      const isHighlighted =
                        selectedRange &&
                        lineNumber >= selectedRange.start &&
                        lineNumber <= selectedRange.end;
                      return (
                        <div
                          key={`${lineNumber}-${line}`}
                          data-line={lineNumber}
                          className={`grid grid-cols-[56px_minmax(0,1fr)] gap-4 rounded px-2 ${
                            isHighlighted ? "bg-accent/12" : ""
                          }`}
                        >
                          <span className="select-none text-right font-mono text-xs text-mist/28">
                            {lineNumber}
                          </span>
                          <code className="whitespace-pre-wrap break-words font-mono text-xs text-mist/88">
                            {line || " "}
                          </code>
                        </div>
                      );
                    })}
                  </pre>
                ) : (
                  <div className="flex h-full items-center justify-center text-sm text-mist/55">
                    No file content available yet.
                  </div>
                )}
              </div>

              <div className="space-y-3">
                <div className="rounded-[24px] border border-white/8 bg-white/5 p-4">
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-mist/50">
                    File Summary
                  </p>
                  <p className="mt-3 text-sm leading-7 text-mist/72">
                    {fileDetailQuery.data?.summary ??
                      "Select a supported file to inspect its extracted summary."}
                  </p>
                </div>
                <div className="rounded-[24px] border border-white/8 bg-white/5 p-4">
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-mist/50">
                    Extracted Chunks
                  </p>
                  <div className="mt-3 max-h-[340px] space-y-2 overflow-auto pr-1">
                    {fileDetailQuery.data?.chunks.map((chunk) => (
                      <button
                        key={chunk.id}
                        type="button"
                        onClick={() =>
                          setHighlightedCitation({
                            chunk_id: chunk.id,
                            file_id: fileDetailQuery.data.id,
                            path: fileDetailQuery.data.path,
                            chunk_type: chunk.chunk_type,
                            symbol_name: chunk.symbol_name,
                            start_line: chunk.start_line,
                            end_line: chunk.end_line,
                            preview: chunk.content.slice(0, 240)
                          })
                        }
                        className="w-full rounded-2xl border border-white/8 bg-[#091525] px-3 py-3 text-left transition hover:border-accent"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-mono text-[11px] uppercase tracking-[0.15em] text-accent">
                            {chunk.chunk_type}
                          </span>
                          <span className="text-xs text-mist/45">
                            {chunk.start_line && chunk.end_line
                              ? `${chunk.start_line}-${chunk.end_line}`
                              : "n/a"}
                          </span>
                        </div>
                        <p className="mt-2 text-sm text-mist/76">
                          {chunk.symbol_name ?? chunk.content.slice(0, 72)}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
