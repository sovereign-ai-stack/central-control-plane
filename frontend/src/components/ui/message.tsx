"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export function MessageGroup({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="message-group"
      className={cn("flex w-full flex-col gap-2", className)}
      {...props}
    />
  );
}

const messageVariants = cva("flex w-full gap-3 text-sm", {
  variants: {
    align: {
      start: "flex-row items-start justify-start text-start",
      end: "flex-row-reverse items-start justify-start text-start",
    },
  },
  defaultVariants: {
    align: "start",
  },
});

export interface MessageProps
  extends React.ComponentProps<"div">,
    VariantProps<typeof messageVariants> {}

export function Message({ className, align = "start", ...props }: MessageProps) {
  return (
    <div
      data-slot="message"
      data-align={align}
      className={cn(messageVariants({ align }), className)}
      {...props}
    />
  );
}

export function MessageAvatar({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="message-avatar"
      className={cn("flex size-8 shrink-0 select-none items-center justify-center rounded-full", className)}
      {...props}
    />
  );
}

export function MessageContent({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="message-content"
      className={cn("flex min-w-0 max-w-[85%] md:max-w-[75%] flex-col gap-1.5", className)}
      {...props}
    />
  );
}

export function MessageHeader({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="message-header"
      className={cn("flex items-center gap-2 text-xs text-muted-foreground", className)}
      {...props}
    />
  );
}

export function MessageFooter({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="message-footer"
      className={cn("flex items-center gap-2 text-xs text-muted-foreground", className)}
      {...props}
    />
  );
}
