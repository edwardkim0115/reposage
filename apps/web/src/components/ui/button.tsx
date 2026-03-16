import { ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "primary", ...props },
  ref
) {
  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-medium transition",
        "disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" &&
          "bg-accent text-ink hover:bg-[#62c8bc] shadow-[0_12px_30px_rgba(72,179,167,0.28)]",
        variant === "secondary" &&
          "border border-line bg-white/5 text-mist hover:border-accent hover:bg-white/10",
        variant === "ghost" && "text-mist/80 hover:bg-white/5 hover:text-mist",
        className
      )}
      {...props}
    />
  );
});

