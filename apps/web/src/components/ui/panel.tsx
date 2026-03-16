import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Panel({
  className,
  children
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <section
      className={cn(
        "rounded-[28px] border border-white/8 bg-panel/90 p-5 shadow-panel backdrop-blur-sm",
        className
      )}
    >
      {children}
    </section>
  );
}
