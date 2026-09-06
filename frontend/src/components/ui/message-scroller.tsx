"use client";

import * as React from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface MessageScrollerContextValue {
  viewportRef: React.RefObject<HTMLDivElement | null>;
  isAtBottom: boolean;
  isScrollable: boolean;
  scrollToBottom: (smooth?: boolean) => void;
  scrollToTop: (smooth?: boolean) => void;
  autoScroll: boolean;
  registerItem: (id: string, element: HTMLElement) => void;
  unregisterItem: (id: string) => void;
}

const MessageScrollerContext = React.createContext<MessageScrollerContextValue | null>(null);

export function useMessageScroller() {
  const context = React.useContext(MessageScrollerContext);
  if (!context) {
    throw new Error("useMessageScroller must be used within a MessageScrollerProvider");
  }
  return context;
}

export function useMessageScrollerVisibility() {
  const context = useMessageScroller();
  return { isAtBottom: context.isAtBottom };
}

export function useMessageScrollerScrollable() {
  const context = useMessageScroller();
  return { isScrollable: context.isScrollable };
}

export interface MessageScrollerProviderProps {
  children: React.ReactNode;
  autoScroll?: boolean;
  isStreaming?: boolean;
}

export function MessageScrollerProvider({
  children,
  autoScroll = true,
  isStreaming = false,
}: MessageScrollerProviderProps) {
  const viewportRef = React.useRef<HTMLDivElement | null>(null);
  const [isAtBottom, setIsAtBottom] = React.useState(true);
  const [isScrollable, setIsScrollable] = React.useState(false);
  const itemsRef = React.useRef<Map<string, HTMLElement>>(new Map());
  const userScrolledUpRef = React.useRef(false);

  const checkScroll = React.useCallback(() => {
    const el = viewportRef.current;
    if (!el) return;

    const threshold = 120;
    const scrollBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    const atBottom = scrollBottom <= threshold;

    if (atBottom) {
      userScrolledUpRef.current = false;
      setIsAtBottom(true);
    } else {
      if (userScrolledUpRef.current) {
        setIsAtBottom(false);
      }
    }
    setIsScrollable(el.scrollHeight > el.clientHeight + 60);
  }, []);

  const scrollToBottom = React.useCallback((smooth = true) => {
    const el = viewportRef.current;
    if (!el) return;
    el.scrollTo({
      top: el.scrollHeight,
      behavior: smooth ? "smooth" : "auto",
    });
    userScrolledUpRef.current = false;
    setIsAtBottom(true);
  }, []);

  const scrollToTop = React.useCallback((smooth = true) => {
    const el = viewportRef.current;
    if (!el) return;
    el.scrollTo({
      top: 0,
      behavior: smooth ? "smooth" : "auto",
    });
  }, []);

  const registerItem = React.useCallback((id: string, element: HTMLElement) => {
    itemsRef.current.set(id, element);
  }, []);

  const unregisterItem = React.useCallback((id: string) => {
    itemsRef.current.delete(id);
  }, []);

  // Track explicit manual user scroll interactions (Wheel, Touch, Keydown)
  React.useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;

    const handleWheel = (e: WheelEvent) => {
      if (e.deltaY < 0) {
        // User scrolled UP
        userScrolledUpRef.current = true;
        setIsAtBottom(false);
      } else if (e.deltaY > 0) {
        // User scrolled DOWN
        const threshold = 120;
        const scrollBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
        if (scrollBottom <= threshold) {
          userScrolledUpRef.current = false;
          setIsAtBottom(true);
        }
      }
    };

    let touchStartY = 0;
    const handleTouchStart = (e: TouchEvent) => {
      touchStartY = e.touches[0]?.clientY || 0;
    };
    const handleTouchMove = (e: TouchEvent) => {
      const currentY = e.touches[0]?.clientY || 0;
      if (currentY > touchStartY + 12) {
        // Dragged downwards => user scrolling UP
        userScrolledUpRef.current = true;
        setIsAtBottom(false);
      } else if (currentY < touchStartY - 12) {
        // Dragged upwards => user scrolling DOWN
        const threshold = 120;
        const scrollBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
        if (scrollBottom <= threshold) {
          userScrolledUpRef.current = false;
          setIsAtBottom(true);
        }
      }
    };

    el.addEventListener("wheel", handleWheel, { passive: true });
    el.addEventListener("touchstart", handleTouchStart, { passive: true });
    el.addEventListener("touchmove", handleTouchMove, { passive: true });
    el.addEventListener("scroll", checkScroll, { passive: true });

    return () => {
      el.removeEventListener("wheel", handleWheel);
      el.removeEventListener("touchstart", handleTouchStart);
      el.removeEventListener("touchmove", handleTouchMove);
      el.removeEventListener("scroll", checkScroll);
    };
  }, [checkScroll]);

  // Keep pinned during active token streaming unless user manually scrolled up
  React.useEffect(() => {
    if (isStreaming && !userScrolledUpRef.current) {
      const el = viewportRef.current;
      if (el) {
        el.scrollTop = el.scrollHeight;
        setIsAtBottom(true);
      }
    }
  }, [isStreaming]);

  // MutationObserver for DOM changes during streaming
  React.useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;

    const observer = new MutationObserver(() => {
      if (autoScroll && !userScrolledUpRef.current) {
        el.scrollTop = el.scrollHeight;
        setIsAtBottom(true);
      } else {
        const threshold = 120;
        const scrollBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
        setIsAtBottom(scrollBottom <= threshold);
      }
      setIsScrollable(el.scrollHeight > el.clientHeight + 60);
    });

    observer.observe(el, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    return () => observer.disconnect();
  }, [autoScroll]);

  return (
    <MessageScrollerContext.Provider
      value={{
        viewportRef,
        isAtBottom,
        isScrollable,
        scrollToBottom,
        scrollToTop,
        autoScroll,
        registerItem,
        unregisterItem,
      }}
    >
      {children}
    </MessageScrollerContext.Provider>
  );
}

export function MessageScroller({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="message-scroller"
      className={cn("relative flex h-full w-full flex-col overflow-hidden", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function MessageScrollerViewport({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) {
  const { viewportRef } = useMessageScroller();

  return (
    <div
      ref={viewportRef}
      data-slot="message-scroller-viewport"
      className={cn(
        "flex-1 overflow-y-auto overflow-x-hidden scroll-smooth",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function MessageScrollerContent({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="message-scroller-content"
      className={cn("flex flex-col gap-6 p-4 md:p-6", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export interface MessageScrollerItemProps extends React.ComponentProps<"div"> {
  messageId?: string;
  scrollAnchor?: boolean;
}

export function MessageScrollerItem({
  messageId,
  scrollAnchor = false,
  className,
  children,
  ...props
}: MessageScrollerItemProps) {
  const itemRef = React.useRef<HTMLDivElement | null>(null);
  const { registerItem, unregisterItem } = useMessageScroller();

  React.useEffect(() => {
    if (messageId && itemRef.current) {
      registerItem(messageId, itemRef.current);
      return () => unregisterItem(messageId);
    }
  }, [messageId, registerItem, unregisterItem]);

  return (
    <div
      ref={itemRef}
      data-slot="message-scroller-item"
      data-message-id={messageId}
      data-scroll-anchor={scrollAnchor ? "true" : undefined}
      className={cn("w-full transition-opacity duration-200", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export interface MessageScrollerButtonProps
  extends Omit<React.ComponentProps<typeof Button>, "onClick"> {
  direction?: "end" | "start";
  label?: string;
  containerClassName?: string;
}

export function MessageScrollerButton({
  direction = "end",
  label = "Jump to latest",
  className,
  containerClassName,
  ...props
}: MessageScrollerButtonProps) {
  const { isAtBottom, scrollToBottom, scrollToTop, isScrollable } = useMessageScroller();
  const visible = direction === "end" ? (!isAtBottom && isScrollable) : true;

  const handleClick = () => {
    if (direction === "start") {
      scrollToTop(true);
    } else {
      scrollToBottom(true);
    }
  };

  return (
    <div
      className={cn(
        "pointer-events-none absolute bottom-40 sm:bottom-44 md:bottom-48 left-1/2 z-30 -translate-x-1/2 transition-all duration-200 ease-out",
        visible
          ? "opacity-100 scale-100 pointer-events-auto"
          : "opacity-0 scale-90 pointer-events-none",
        containerClassName
      )}
    >
      <Button
        variant="secondary"
        size="sm"
        className={cn(
          "shadow-2xl gap-1.5 rounded-full border border-border/60 bg-surface-raised/95 hover:bg-surface-active text-foreground backdrop-blur-md text-xs font-medium active:scale-95 transition-all duration-200 cursor-pointer px-3.5 py-1.5 hover:border-brand-cyan/40 hover:shadow-brand-cyan/10",
          className
        )}
        onClick={handleClick}
        aria-label={label}
        {...props}
      >
        {direction === "start" ? (
          <ArrowUp className="size-3.5 text-brand-cyan shrink-0" />
        ) : (
          <ArrowDown className="size-3.5 text-brand-cyan shrink-0 animate-bounce" />
        )}
        <span className="decorative-font font-medium">{label}</span>
      </Button>
    </div>
  );
}
