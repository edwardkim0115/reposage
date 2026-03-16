import { cn } from "@/lib/utils";

const statusStyles: Record<string, string> = {
  created: "bg-white/10 text-mist",
  queued: "bg-amber/20 text-amber",
  indexing: "bg-accent/20 text-accent",
  embedding: "bg-accent/20 text-accent",
  ready: "bg-[#123c34] text-[#80ebd7]",
  failed: "bg-rose/20 text-rose"
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]",
        statusStyles[status] ?? "bg-white/10 text-mist"
      )}
    >
      {status}
    </span>
  );
}

