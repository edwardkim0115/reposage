import { ProjectWorkspace } from "@/components/project-workspace";

export default function ProjectPage({ params }: { params: { id: string } }) {
  return <ProjectWorkspace projectId={params.id} />;
}

