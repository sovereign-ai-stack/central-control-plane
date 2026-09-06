"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";

const markerVariants = cva("flex items-center gap-2 text-xs text-muted-foreground", {
  variants: {
    variant: {
      default: "w-full justify-center py-2",
      separator: "relative w-full justify-center py-3",
      border: "w-full border-b border-border py-2",
    },
  },
  defaultVariants: {
    variant: "default",
  },
});

export interface MarkerProps
  extends React.ComponentProps<"div">,
    VariantProps<typeof markerVariants> {}

export function Marker({
  className,
  variant = "default",
  children,
  ...props
}: MarkerProps) {
  if (variant === "separator") {
    return (
      <div
        data-slot="marker"
        data-variant={variant}
        className={cn(markerVariants({ variant }), className)}
        {...props}
      >
        <Separator className="absolute inset-0 top-1/2" />
        <div className="relative z-10 flex items-center gap-2 bg-background px-3 font-medium">
          {children}
        </div>
      </div>
    );
  }

  return (
    <div
      data-slot="marker"
      data-variant={variant}
      className={cn(markerVariants({ variant }), className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function MarkerIcon({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="marker-icon"
      className={cn("flex size-4 shrink-0 items-center justify-center [&>svg]:size-3.5", className)}
      {...props}
    />
  );
}

export function MarkerContent({
  className,
  ...props
}: React.ComponentProps<"span">) {
  return (
    <span
      data-slot="marker-content"
      className={cn("inline-flex items-center gap-1.5", className)}
      {...props}
    />
  );
}
