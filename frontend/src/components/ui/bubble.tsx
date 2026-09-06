"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const bubbleVariants = cva(
  "relative rounded-2xl px-4 py-3 text-sm leading-relaxed transition-colors break-words",
  {
    variants: {
      variant: {
        default: "bg-surface-raised text-foreground border border-border/60 shadow-xs",
        secondary: "bg-secondary text-secondary-foreground",
        muted: "bg-muted text-muted-foreground",
        tinted: "bg-brand-cyan/10 text-foreground border border-brand-cyan/20",
        outline: "border border-border bg-transparent text-foreground",
        ghost: "bg-transparent text-foreground p-0 border-0 shadow-none",
        destructive: "bg-destructive/10 text-destructive border border-destructive/20",
      },
      align: {
        start: "rounded-tl-sm",
        end: "rounded-tr-sm bg-surface-active/80 text-foreground border border-border/80",
      },
    },
    defaultVariants: {
      variant: "default",
      align: "start",
    },
  }
);

export interface BubbleProps
  extends React.ComponentProps<"div">,
    VariantProps<typeof bubbleVariants> {}

export function Bubble({
  className,
  variant = "default",
  align = "start",
  children,
  ...props
}: BubbleProps) {
  return (
    <div
      data-slot="bubble"
      data-variant={variant}
      data-align={align}
      className={cn(bubbleVariants({ variant, align }), className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function BubbleContent({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="bubble-content"
      className={cn("flex flex-col gap-2", className)}
      {...props}
    />
  );
}

const bubbleReactionsVariants = cva("absolute flex items-center gap-1", {
  variants: {
    side: {
      top: "-top-3",
      bottom: "-bottom-3",
    },
    align: {
      start: "start-2",
      end: "end-2",
    },
  },
  defaultVariants: {
    side: "bottom",
    align: "end",
  },
});

export interface BubbleReactionsProps
  extends React.ComponentProps<"div">,
    VariantProps<typeof bubbleReactionsVariants> {}

export function BubbleReactions({
  className,
  side = "bottom",
  align = "end",
  ...props
}: BubbleReactionsProps) {
  return (
    <div
      data-slot="bubble-reactions"
      className={cn(bubbleReactionsVariants({ side, align }), className)}
      {...props}
    />
  );
}
