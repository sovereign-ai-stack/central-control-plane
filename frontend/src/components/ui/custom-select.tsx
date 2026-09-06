"use client";

import * as React from "react";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CustomSelectOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
  badge?: string;
}

export interface CustomSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: CustomSelectOption[];
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

export function CustomSelect({
  value,
  onChange,
  options,
  placeholder = "انتخاب کنید...",
  className,
  disabled = false,
}: CustomSelectProps) {
  const [open, setOpen] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);

  const selectedOption = options.find((opt) => opt.value === value);

  // Close on outside click
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [open]);

  return (
    <div ref={containerRef} className={cn("relative w-full text-xs", className)}>
      {/* Trigger Button with rounded-2xl */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          "w-full h-9 px-3 bg-[#181a24] hover:bg-[#1e202c] border border-border/80 text-foreground font-medium rounded-2xl flex items-center justify-between gap-2 transition-all duration-200 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-cyan/40 focus:border-brand-cyan cursor-pointer",
          open && "ring-2 ring-brand-cyan/40 border-brand-cyan bg-[#1e202c]",
          disabled && "opacity-50 cursor-not-allowed pointer-events-none"
        )}
      >
        <div className="flex items-center gap-2 truncate text-start">
          {selectedOption ? (
            <>
              {selectedOption.icon && <span className="shrink-0">{selectedOption.icon}</span>}
              <span className="truncate">{selectedOption.label}</span>
              {selectedOption.badge && (
                <span className="text-[10px] bg-brand-cyan/15 text-brand-cyan px-1.5 py-0.5 rounded-full font-mono">
                  {selectedOption.badge}
                </span>
              )}
            </>
          ) : (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
        </div>
        <ChevronDown
          className={cn(
            "size-3.5 text-muted-foreground shrink-0 transition-transform duration-200",
            open && "rotate-180 text-brand-cyan"
          )}
        />
      </button>

      {/* Floating Animated Popover Menu with Rounded Corners (rounded-2xl) */}
      {open && (
        <div className="absolute top-full start-0 z-50 mt-1.5 w-full min-w-[200px] max-h-60 overflow-y-auto rounded-2xl border border-border/90 bg-[#151722]/95 p-1.5 shadow-2xl backdrop-blur-xl animate-in fade-in-0 zoom-in-95 duration-150 space-y-1 focus:outline-none">
          {options.length === 0 ? (
            <div className="px-3 py-2 text-center text-muted-foreground text-[11px]">
              موردی یافت نشد
            </div>
          ) : (
            options.map((option) => {
              const isSelected = option.value === value;
              return (
                <div
                  key={option.value}
                  onClick={() => {
                    onChange(option.value);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex items-center justify-between gap-2 px-3 py-2 rounded-xl cursor-pointer text-xs font-medium transition-colors select-none",
                    isSelected
                      ? "bg-brand-cyan/15 text-brand-cyan font-bold"
                      : "text-foreground/90 hover:bg-surface-raised hover:text-foreground"
                  )}
                >
                  <div className="flex items-center gap-2 truncate">
                    {option.icon && <span className="shrink-0">{option.icon}</span>}
                    <span className="truncate">{option.label}</span>
                    {option.badge && (
                      <span className="text-[10px] bg-surface text-muted-foreground px-1.5 py-0.5 rounded-md font-mono">
                        {option.badge}
                      </span>
                    )}
                  </div>
                  {isSelected && <Check className="size-3.5 text-brand-cyan shrink-0 stroke-[2.5]" />}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
