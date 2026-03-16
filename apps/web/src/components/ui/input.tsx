import { InputHTMLAttributes, forwardRef } from "react";

import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full rounded-2xl border border-line bg-[#091525]/90 px-4 py-3 text-sm text-mist outline-none transition",
          "placeholder:text-mist/35 focus:border-accent focus:ring-2 focus:ring-accent/20",
          className
        )}
        {...props}
      />
    );
  }
);

