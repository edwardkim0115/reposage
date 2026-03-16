"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderPlus, Github, Layers3, Upload } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { api } from "@/lib/api";
import { formatDate, truncate } from "@/lib/utils";

export function ProjectsScreen() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [githubName, setGithubName] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [uploadName, setUploadName] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [emptyProjectName, setEmptyProjectName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: api.listProjects,
    refetchInterval: 5000
  });

  const githubMutation = useMutation({
    mutationFn: api.createGithubProject,
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      router.push(`/projects/${project.id}`);
    },
    onError: (mutationError: Error) => setError(mutationError.message)
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadFile) throw new Error("Select a ZIP file to upload.");
      return api.uploadZipProject(uploadName, uploadFile);
    },
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      router.push(`/projects/${project.id}`);
    },
    onError: (mutationError: Error) => setError(mutationError.message)
  });

  const createProjectMutation = useMutation({
    mutationFn: () => api.createProject(emptyProjectName),
    onSuccess: async () => {
      setEmptyProjectName("");
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (mutationError: Error) => setError(mutationError.message)
  });

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
      <header className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
        <Panel className="overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(72,179,167,0.2),transparent_45%),linear-gradient(180deg,rgba(16,31,53,0.96),rgba(9,19,33,0.98))]">
          <div className="space-y-5">
            <span className="inline-flex rounded-full border border-white/10 px-3 py-1 font-mono text-xs uppercase tracking-[0.22em] text-accent">
              Grounded Codebase QA
            </span>
            <div className="space-y-3">
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                RepoSage turns a repository into something you can interrogate with evidence.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-mist/72">
                Ingest a public GitHub repository or local ZIP, index code and docs with semantic
                chunks, and ask real questions with file citations and line-aware context.
              </p>
            </div>
            <div className="grid gap-3 text-sm text-mist/75 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                Hybrid search with lexical + vector retrieval
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                Async indexing backed by Postgres, pgvector, and Redis
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                File browsing and citation-linked source previews
              </div>
            </div>
          </div>
        </Panel>

        <Panel>
          <div className="space-y-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-mist/50">
                Create Empty Project
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-white">Start clean</h2>
            </div>
            <Input
              value={emptyProjectName}
              onChange={(event) => setEmptyProjectName(event.target.value)}
              placeholder="Architecture review"
            />
            <Button
              className="w-full"
              onClick={() => {
                setError(null);
                createProjectMutation.mutate();
              }}
              disabled={!emptyProjectName.trim() || createProjectMutation.isPending}
            >
              <FolderPlus className="mr-2 h-4 w-4" />
              Create project shell
            </Button>
          </div>
        </Panel>
      </header>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel>
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-mist/50">
                GitHub Ingestion
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-white">Public repository URL</h2>
            </div>
            <Github className="h-5 w-5 text-accent" />
          </div>
          <div className="space-y-3">
            <Input
              value={githubName}
              onChange={(event) => setGithubName(event.target.value)}
              placeholder="Example: FastAPI source explorer"
            />
            <Input
              value={githubUrl}
              onChange={(event) => setGithubUrl(event.target.value)}
              placeholder="https://github.com/owner/repo"
            />
            <Button
              className="w-full"
              onClick={() => {
                setError(null);
                githubMutation.mutate({ name: githubName, source_url: githubUrl });
              }}
              disabled={!githubName.trim() || !githubUrl.trim() || githubMutation.isPending}
            >
              <Layers3 className="mr-2 h-4 w-4" />
              Create and index GitHub project
            </Button>
          </div>
        </Panel>

        <Panel>
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-mist/50">
                ZIP Ingestion
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-white">Local archive upload</h2>
            </div>
            <Upload className="h-5 w-5 text-amber" />
          </div>
          <div className="space-y-3">
            <Input
              value={uploadName}
              onChange={(event) => setUploadName(event.target.value)}
              placeholder="Example: Billing monolith"
            />
            <Input
              type="file"
              accept=".zip"
              onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
            />
            <Button
              className="w-full"
              onClick={() => {
                setError(null);
                uploadMutation.mutate();
              }}
              disabled={!uploadName.trim() || !uploadFile || uploadMutation.isPending}
            >
              <Upload className="mr-2 h-4 w-4" />
              Upload and index ZIP
            </Button>
          </div>
        </Panel>
      </section>

      {error ? (
        <div className="rounded-3xl border border-rose/30 bg-rose/10 px-5 py-4 text-sm text-rose">
          {error}
        </div>
      ) : null}

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-mist/50">Projects</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">Indexing workspace</h2>
          </div>
          <span className="text-sm text-mist/60">
            {projectsQuery.data?.length ?? 0} tracked repositories
          </span>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {projectsQuery.data?.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}`}>
              <Panel className="h-full transition hover:-translate-y-1 hover:border-accent/60">
                <div className="flex h-full flex-col gap-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="text-xl font-semibold text-white">{project.name}</h3>
                      <p className="mt-2 text-sm text-mist/60">
                        {project.source_url
                          ? truncate(project.source_url, 56)
                          : "No source attached yet"}
                      </p>
                    </div>
                    <StatusBadge status={project.status} />
                  </div>
                  <div className="grid gap-2 text-sm text-mist/60">
                    <p>Source type: {project.source_type ?? "manual"}</p>
                    <p>Updated: {formatDate(project.updated_at)}</p>
                    <p>Last indexed: {formatDate(project.last_indexed_at)}</p>
                  </div>
                </div>
              </Panel>
            </Link>
          ))}
          {!projectsQuery.data?.length ? (
            <Panel className="lg:col-span-2">
              <p className="text-sm text-mist/60">
                No projects yet. Start with a public GitHub URL or upload a ZIP archive.
              </p>
            </Panel>
          ) : null}
        </div>
      </section>
    </div>
  );
}

