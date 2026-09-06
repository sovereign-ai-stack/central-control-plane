"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export function AttachmentGroup({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="attachment-group"
      className={cn("flex flex-wrap gap-2", className)}
      {...props}
    />
  );
}

const attachmentVariants = cva(
  "group/attachment relative flex items-center gap-3 rounded-lg border border-border bg-surface-raised p-2.5 transition-colors",
  {
    variants: {
      size: {
        default: "p-2.5 text-sm",
        sm: "p-2 text-xs",
        xs: "p-1.5 text-xs",
      },
      orientation: {
        horizontal: "flex-row",
        vertical: "flex-col items-start",
      },
      state: {
        idle: "",
        uploading: "opacity-80",
        processing: "opacity-80",
        error: "border-destructive/50 bg-destructive/5",
        done: "",
      },
    },
    defaultVariants: {
      size: "default",
      orientation: "horizontal",
      state: "idle",
    },
  }
);

export interface AttachmentProps
  extends React.ComponentProps<"div">,
    VariantProps<typeof attachmentVariants> {}

export function Attachment({
  className,
  size = "default",
  orientation = "horizontal",
  state = "idle",
  children,
  ...props
}: AttachmentProps) {
  return (
    <div
      data-slot="attachment"
      data-state={state}
      data-size={size}
      className={cn(attachmentVariants({ size, orientation, state }), className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function AttachmentMedia({
  className,
  variant = "icon",
  children,
  ...props
}: React.ComponentProps<"div"> & { variant?: "icon" | "image" }) {
  return (
    <div
      data-slot="attachment-media"
      data-variant={variant}
      className={cn(
        "flex size-9 shrink-0 items-center justify-center rounded-md bg-surface text-muted-foreground [&>svg]:size-5 overflow-hidden",
        variant === "image" && "bg-transparent",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function AttachmentContent({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="attachment-content"
      className={cn("flex min-w-0 flex-1 flex-col gap-0.5", className)}
      {...props}
    />
  );
}

export function AttachmentTitle({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="attachment-title"
      className={cn(
        "truncate font-medium text-foreground",
        "group-data-[state=uploading]/attachment:shimmer group-data-[state=processing]/attachment:shimmer",
        className
      )}
      {...props}
    />
  );
}

export function AttachmentDescription({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="attachment-description"
      className={cn("truncate text-xs text-muted-foreground", className)}
      {...props}
    />
  );
}

export function AttachmentActions({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="attachment-actions"
      className={cn("flex shrink-0 items-center gap-1", className)}
      {...props}
    />
  );
}

export function AttachmentAction({
  className,
  ...props
}: React.ComponentProps<"button">) {
  return (
    <button
      type="button"
      data-slot="attachment-action"
      className={cn(
        "flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-surface-active hover:text-foreground transition-colors [&>svg]:size-4",
        className
      )}
      {...props}
    />
  );
}
