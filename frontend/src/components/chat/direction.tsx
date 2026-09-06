"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { detectDirection } from "@/lib/locale";
import type { Language } from "@/lib/types";

export interface DirectionBoundaryProps extends React.ComponentProps<"div"> {
  language?: Language;
  content?: string;
  forceDir?: "rtl" | "ltr" | "auto";
}

export function DirectionBoundary({
  language,
  content,
  forceDir,
  className,
  children,
  ...props
}: DirectionBoundaryProps) {
  const detectedDir = content ? detectDirection(content) : language === "fa" ? "rtl" : "ltr";
  const dir = forceDir && forceDir !== "auto" ? forceDir : detectedDir;

  return (
    <div
      dir={dir}
      className={cn(dir === "rtl" ? "text-right" : "text-left", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export interface IsolatedLtrProps extends React.ComponentProps<"span"> {
  as?: "span" | "code";
}

export function IsolatedLtr({
  as: Component = "span",
  className,
  children,
  ...props
}: IsolatedLtrProps) {
  if (Component === "code") {
    return (
      <code
        dir="ltr"
        className={cn("inline-block text-left font-mono font-normal tracking-tight [unicode-bidi:isolate]", className)}
        {...(props as React.ComponentProps<"code">)}
      >
        {children}
      </code>
    );
  }

  return (
    <span
      dir="ltr"
      className={cn("inline-block text-left font-mono font-normal tracking-tight [unicode-bidi:isolate]", className)}
      {...props}
    >
      {children}
    </span>
  );
}
