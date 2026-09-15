"use client";

import * as React from "react";
import { Check, Copy } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export interface CodeBlockProps extends React.ComponentProps<"div"> {
  code: string;
  language?: string;
  filename?: string;
}

const languageAliases: Record<string, string> = {
  csharp: "c#",
  cs: "c#",
  html: "markup",
  js: "javascript",
  jsonc: "json",
  md: "markdown",
  ps: "powershell",
  py: "python",
  sh: "bash",
  shell: "bash",
  ts: "typescript",
  yml: "yaml",
};

const keywords: Record<string, Set<string>> = {
  bash: new Set(["case", "do", "done", "elif", "else", "esac", "fi", "for", "function", "if", "in", "then", "until", "while"]),
  c: new Set(["auto", "break", "case", "char", "const", "continue", "default", "do", "double", "else", "enum", "extern", "float", "for", "goto", "if", "int", "long", "return", "short", "signed", "sizeof", "static", "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while"]),
  "c#": new Set(["async", "await", "bool", "class", "const", "else", "for", "if", "in", "int", "interface", "namespace", "new", "null", "private", "public", "return", "static", "string", "using", "void", "while"]),
  css: new Set(["@media", "@supports", "display", "flex", "grid", "important", "position", "relative", "absolute"]),
  go: new Set(["break", "case", "chan", "const", "continue", "default", "defer", "else", "for", "func", "go", "goto", "if", "import", "interface", "map", "package", "range", "return", "select", "struct", "switch", "type", "var"]),
  java: new Set(["abstract", "boolean", "break", "case", "catch", "class", "const", "continue", "default", "do", "else", "extends", "final", "finally", "for", "if", "implements", "import", "instanceof", "int", "interface", "new", "null", "package", "private", "protected", "public", "return", "static", "this", "throw", "try", "void", "while"]),
  javascript: new Set(["async", "await", "break", "case", "catch", "class", "const", "continue", "debugger", "default", "delete", "do", "else", "export", "extends", "finally", "for", "from", "function", "if", "import", "in", "instanceof", "let", "new", "null", "of", "return", "static", "super", "switch", "this", "throw", "try", "typeof", "undefined", "var", "void", "while", "with", "yield"]),
  json: new Set(["false", "null", "true"]),
  markdown: new Set(["blockquote", "code", "emphasis", "heading", "image", "link", "list", "table"]),
  php: new Set(["abstract", "and", "array", "as", "break", "callable", "case", "catch", "class", "const", "continue", "declare", "default", "die", "do", "echo", "else", "elseif", "empty", "extends", "final", "finally", "for", "foreach", "function", "global", "if", "implements", "include", "instanceof", "interface", "namespace", "new", "or", "private", "protected", "public", "require", "return", "static", "switch", "throw", "trait", "try", "use", "var", "while", " xor "]),
  powershell: new Set(["begin", "break", "catch", "class", "continue", "do", "else", "elseif", "end", "exit", "filter", "finally", "for", "foreach", "function", "if", "in", "param", "process", "return", "switch", "throw", "trap", "try", "until", "while"]),
  python: new Set(["and", "as", "assert", "async", "await", "break", "case", "class", "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "match", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"]),
  ruby: new Set(["begin", "break", "case", "class", "def", "do", "else", "elsif", "end", "ensure", "for", "if", "in", "module", "next", "nil", "not", "or", "redo", "rescue", "retry", "return", "then", "self", "super", "unless", "until", "when", "while", "yield"]),
  rust: new Set(["as", "async", "await", "break", "const", "continue", "crate", "dyn", "else", "enum", "extern", "false", "fn", "for", "if", "impl", "in", "let", "loop", "match", "mod", "move", "mut", "pub", "ref", "return", "self", "Self", "static", "struct", "super", "trait", "true", "type", "unsafe", "use", "where", "while"]),
  sql: new Set(["alter", "and", "as", "asc", "begin", "by", "case", "create", "delete", "desc", "drop", "else", "end", "from", "group", "having", "in", "insert", "into", "is", "join", "left", "like", "limit", "not", "null", "on", "or", "order", "select", "set", "table", "then", "union", "update", "values", "when", "where", "with"]),
  typescript: new Set(["as", "async", "await", "break", "case", "catch", "class", "const", "continue", "debugger", "default", "delete", "do", "else", "enum", "export", "extends", "finally", "for", "from", "function", "if", "implements", "import", "in", "infer", "instanceof", "interface", "keyof", "let", "namespace", "never", "new", "null", "of", "private", "protected", "public", "readonly", "return", "satisfies", "static", "string", "super", "switch", "this", "throw", "try", "type", "typeof", "undefined", "unknown", "var", "void", "while", "with", "yield"]),
  yaml: new Set(["false", "null", "true"]),
};

function normalizeLanguage(language: string) {
  const normalized = language.toLowerCase();
  return languageAliases[normalized] || normalized;
}

function classifyToken(token: string, language: string, nextCharacter: string) {
  if (/^(\/\/|\/\*|#)/.test(token)) return "text-slate-400 italic";
  if (/^(\"|'|\x60)/.test(token)) return "text-amber-300";
  if (/^\d/.test(token)) return "text-orange-300";

  const normalizedLanguage = normalizeLanguage(language);
  const languageKeywords = keywords[normalizedLanguage] || keywords.javascript;
  if (languageKeywords.has(token)) return "text-sky-300 font-semibold";
  if (token === "true" || token === "false" || token === "null" || token === "None" || token === "undefined") {
    return "text-fuchsia-300";
  }
  if (/^[A-Za-z_$][\w$]*$/.test(token) && nextCharacter === "(") return "text-violet-300";
  if (/^[{}()[\].,;:+\-*/%=<>!?|&~^]+$/.test(token)) return "text-cyan-300";
  return "text-on-surface";
}

function highlightCode(code: string, language: string) {
  const tokens: React.ReactNode[] = [];
  const tokenPattern = /(\/\/[^\n]*|\/\*[\s\S]*?\*\/|#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\x60(?:\\.|[^\x60\\])*\x60|\b\d+(?:\.\d+)?\b|\b[A-Za-z_$][\w$]*\b|=>|===?|!==?|<=|>=|&&|\|\||[{}()[\].,;:+\-*/%=<>!?|&~^]+)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let tokenIndex = 0;

  while ((match = tokenPattern.exec(code))) {
    if (match.index > lastIndex) tokens.push(code.slice(lastIndex, match.index));

    const token = match[0];
    tokens.push(
      <span key={`token-${tokenIndex}`} className={classifyToken(token, language, code[tokenPattern.lastIndex] || "")}>
        {token}
      </span>
    );
    tokenIndex += 1;
    lastIndex = tokenPattern.lastIndex;
  }

  if (lastIndex < code.length) tokens.push(code.slice(lastIndex));
  return tokens;
}

export function CodeBlock({
  code,
  language = "bash",
  filename,
  className,
  ...props
}: CodeBlockProps) {
  const [copied, setCopied] = React.useState(false);
  const highlightedCode = React.useMemo(() => highlightCode(code, language), [code, language]);

  const onCopy = async () => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(code);
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = code;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        const ok = document.execCommand("copy");
        document.body.removeChild(textArea);
        if (!ok) throw new Error("Copy command failed");
      }
      setCopied(true);
      toast.success("کد در کلیپ‌بورد کپی شد");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("خطا در کپی کردن کد");
    }
  };

  const title = filename || language;

  return (
    <div
      dir="ltr"
      role="region"
      aria-label="Code snippet"
      data-slot="code-block"
      className={cn(
        "bg-[#0d1117] rounded-xl my-5 overflow-hidden border border-white/10 text-left shadow-sm",
        className
      )}
      {...props}
    >
      {/* Code Header bar */}
      <div className="flex justify-between items-center bg-[#161b22]/90 px-4 py-1.5 border-b border-white/5 select-none">
        <span className="text-[12px] font-medium text-slate-400 lowercase font-sans">
          {title}
        </span>
        <button
          type="button"
          onClick={onCopy}
          className="text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1.5 text-[12px] font-sans px-2 py-1 rounded-md cursor-pointer active:scale-95"
          aria-label="Copy code"
        >
          {copied ? (
            <>
              <Check className="size-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="size-3.5" />
              <span>Copy code</span>
            </>
          )}
        </button>
      </div>

      {/* Code Body */}
      <div className="p-4 overflow-x-auto bg-[#0d1117]">
        <pre className="font-mono text-[13.5px] leading-[1.6] tracking-tight whitespace-pre [unicode-bidi:isolate] text-slate-200">
          <code dir="ltr" className="font-mono">{highlightedCode}</code>
        </pre>
      </div>
    </div>
  );
}
