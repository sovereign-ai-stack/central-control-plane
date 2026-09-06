"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { BookOpen, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { CodeBlock } from "./code";
import { MathText } from "./math";
import type { Citation } from "@/lib/types";

export interface MarkdownContentProps extends React.ComponentProps<"div"> {
  content: string;
  citations?: Citation[];
  onCitationClick?: (citation: Citation) => void;
}

function MarkdownCode({
  inline,
  className: codeClassName,
  children,
}: React.ComponentProps<"code"> & { inline?: boolean }) {
  const match = /language-([\w+-]+)/.exec(codeClassName || "");
  const codeString = String(children).replace(/\n$/, "");

  if (!inline && (match || codeString.includes("\n"))) {
    return (
      <CodeBlock
        code={codeString}
        language={match ? match[1] : "text"}
      />
    );
  }

  return (
    <span
      dir="ltr"
      data-math-ignore="true"
      className="inline-block font-mono bg-surface-container-low/90 backdrop-blur-sm px-2 py-0.5 rounded-lg text-[#59dcb0] border border-border/30 text-[13px] mx-0.5 align-middle shadow-inner [unicode-bidi:isolate]"
    >
      {children}
    </span>
  );
}

function MarkdownPre({ children }: { children?: React.ReactNode }) {
  return <>{children}</>;
}

function renderMathChildren(children: React.ReactNode): React.ReactNode {
  if (typeof children === "string") {
    return <MathText>{children}</MathText>;
  }
  return children;
}

function omitNode<T extends { node?: unknown }>(props: T) {
  const cleanProps = { ...props };
  delete cleanProps.node;
  return cleanProps;
}

function extractText(node: React.ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (React.isValidElement<{ children?: React.ReactNode }>(node)) {
    return extractText(node.props.children);
  }
  return "";
}

export function MarkdownContent({
  content,
  citations,
  onCitationClick,
  className,
  ...props
}: MarkdownContentProps) {
  // Replace raw citation patterns like [1], [2] with named reference titles from citations
  const processedContent = React.useMemo(() => {
    if (!content) return "";
    if (!citations || citations.length === 0) return content;

    // Transform isolated citation numbers [1], [2] into titled references
    return content.replace(/\[(\d+)\](?!\()/g, (match, digitStr) => {
      const num = parseInt(digitStr, 10);
      const citation = citations[num - 1] || citations[num];
      if (citation && citation.title) {
        return `[${citation.title}](#citation-${num > 0 ? num - 1 : 0})`;
      }
      return match;
    });
  }, [content, citations]);

  return (
    <div
      data-slot="markdown-content"
      className={cn(
        "markdown-content prose prose-invert max-w-none text-[15px] md:text-[16px] leading-relaxed text-on-surface decorative-font [unicode-bidi:plaintext]",
        "prose-headings:text-foreground prose-headings:font-bold prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-headings:mt-4 prose-headings:mb-2",
        "prose-p:my-3 prose-p:leading-relaxed",
        "prose-ul:my-2 prose-ul:list-disc prose-ul:ps-5",
        "prose-ol:my-2 prose-ol:list-decimal prose-ol:ps-5",
        "prose-li:my-1",
        "prose-blockquote:border-s-4 prose-blockquote:border-brand-cyan/40 prose-blockquote:bg-surface-container-low/40 prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:rounded-r-md prose-blockquote:my-3 prose-blockquote:text-on-surface-variant",
        "prose-hr:my-4 prose-hr:border-border/40",
        "prose-table:w-full prose-table:my-3 prose-table:border-collapse",
        "prose-th:border prose-th:border-border/40 prose-th:bg-surface-raised prose-th:p-2.5 prose-th:text-start prose-th:font-semibold",
        "prose-td:border prose-td:border-border/30 prose-td:p-2.5",
        className
      )}
      {...props}
      dir="auto"
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre: MarkdownPre,
          code: MarkdownCode,
          p({ children, ...paragraphProps }) {
            const cleanProps = omitNode(paragraphProps);
            return (
              <p {...cleanProps} dir="auto">
                {renderMathChildren(children)}
              </p>
            );
          },
          li({ children, ...listItemProps }) {
            const cleanProps = omitNode(listItemProps);
            return (
              <li {...cleanProps} dir="auto">
                {renderMathChildren(children)}
              </li>
            );
          },
          blockquote({ children, ...blockquoteProps }) {
            const cleanProps = omitNode(blockquoteProps);
            return (
              <blockquote {...cleanProps} dir="auto">
                {renderMathChildren(children)}
              </blockquote>
            );
          },
          h1({ children, ...headingProps }) {
            const cleanProps = omitNode(headingProps);
            return <h1 {...cleanProps} dir="auto">{renderMathChildren(children)}</h1>;
          },
          h2({ children, ...headingProps }) {
            const cleanProps = omitNode(headingProps);
            return <h2 {...cleanProps} dir="auto">{renderMathChildren(children)}</h2>;
          },
          h3({ children, ...headingProps }) {
            const cleanProps = omitNode(headingProps);
            return <h3 {...cleanProps} dir="auto">{renderMathChildren(children)}</h3>;
          },
          h4({ children, ...headingProps }) {
            const cleanProps = omitNode(headingProps);
            return <h4 {...cleanProps} dir="auto">{renderMathChildren(children)}</h4>;
          },
          h5({ children, ...headingProps }) {
            const cleanProps = omitNode(headingProps);
            return <h5 {...cleanProps} dir="auto">{renderMathChildren(children)}</h5>;
          },
          h6({ children, ...headingProps }) {
            const cleanProps = omitNode(headingProps);
            return <h6 {...cleanProps} dir="auto">{renderMathChildren(children)}</h6>;
          },
          ul({ children, ...listProps }) {
            const cleanProps = omitNode(listProps);
            return <ul {...cleanProps} dir="auto">{renderMathChildren(children)}</ul>;
          },
          ol({ children, ...listProps }) {
            const cleanProps = omitNode(listProps);
            return <ol {...cleanProps} dir="auto">{renderMathChildren(children)}</ol>;
          },
          table({ children, ...tableProps }) {
            const cleanProps = omitNode(tableProps);
            return <table {...cleanProps} dir="auto">{renderMathChildren(children)}</table>;
          },
          th({ children, ...cellProps }) {
            const cleanProps = omitNode(cellProps);
            return <th {...cleanProps} dir="auto">{renderMathChildren(children)}</th>;
          },
          td({ children, ...cellProps }) {
            const cleanProps = omitNode(cellProps);
            return <td {...cleanProps} dir="auto">{renderMathChildren(children)}</td>;
          },
          a({ href, children, ...linkProps }) {
            const cleanProps = omitNode(linkProps);
            const isCitationHash = typeof href === "string" && href.startsWith("#citation-");
            let citation: Citation | undefined;

            if (isCitationHash && citations) {
              const index = parseInt(href.replace("#citation-", ""), 10);
              citation = citations[index];
            } else if (citations && typeof href === "string") {
              citation = citations.find((c) => c.url === href);
            }

            // Determine friendly source title instead of [1] or raw URL
            const childText = extractText(children);
            const isNumberOnly = /^\[?\d+\]?$/.test(childText.trim());
            const isRawUrl = /^https?:\/\//.test(childText.trim());

            let titleText = childText;
            if (citation?.title && (isNumberOnly || isRawUrl || isCitationHash)) {
              titleText = citation.title;
            } else if (isNumberOnly && citation) {
              titleText = citation.title || citation.section || "مستندات";
            }

            if (!citation && !isCitationHash) {
              return (
                <a
                  {...cleanProps}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand-cyan hover:underline transition-colors"
                  dir="auto"
                >
                  {children}
                </a>
              );
            }

            const targetUrl = citation?.url || href || "#";
            return (
              <a
                {...cleanProps}
                href={targetUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => {
                  if (citation || isCitationHash) {
                    e.preventDefault();
                    if (citation) {
                      onCitationClick?.(citation);
                    }
                  }
                }}
                dir="auto"
                className="inline-flex items-center gap-1.5 text-[12px] font-medium text-brand-cyan hover:text-[#b2ebff] bg-brand-cyan/10 hover:bg-brand-cyan/20 border border-brand-cyan/25 px-2.5 py-0.5 rounded-lg mx-1 my-0.5 transition-all cursor-pointer no-underline align-middle decorative-font shadow-xs group"
                title={citation?.title || titleText}
              >
                <BookOpen className="size-3 shrink-0 opacity-80 group-hover:opacity-100 text-brand-cyan" />
                <span className="truncate max-w-[280px]">{titleText}</span>
              </a>
            );
          },
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}
