import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import { Composer } from "./composer";
import { CodeBlock } from "./code";
import { MarkdownContent } from "./content";
import { Thread } from "./thread";
import { WorkflowProgress } from "../workflow/progress";
import { SourceCard } from "../sources/source-card";
import { AccountPanel } from "../account/account-panel";
import { EmptyChat } from "./empty-chat";
import type { Citation, Message as MessageType, Workflow } from "@/lib/types";

describe("Frontend UI Component Tests (T058 / US4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("CodeBlock Component", () => {
    it("should render code in isolated LTR direction with language badge", () => {
      const code = 'sovereign-agent register --port 8000';
      render(<CodeBlock code={code} language="bash" />);

      const codeContainer = screen.getByRole("region", { name: /code snippet/i });
      expect(codeContainer).toHaveAttribute("dir", "ltr");
      expect(screen.getByText("bash")).toBeInTheDocument();
      expect(codeContainer.querySelector("code")).toHaveTextContent(code);
      expect(codeContainer.querySelectorAll("code span").length).toBeGreaterThan(0);
    });

    it("should copy code to clipboard when copy button is clicked", async () => {
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: {
          writeText: writeTextMock,
        },
      });

      const code = 'DATABASE_URL="postgresql://user:pass@host:5432/db"';
      render(<CodeBlock code={code} language="env" />);

      const copyBtn = screen.getByRole("button", { name: /copy/i });
      await act(async () => {
        fireEvent.click(copyBtn);
      });

      expect(writeTextMock).toHaveBeenCalledWith(code);
    });
  });

  describe("MarkdownContent Component", () => {
    it("should render markdown with safe link targets and isolated LTR for technical terms", () => {
      const markdown = `
برای اجرای نود از دستور زیر استفاده کنید:
\`sovereign-agent start\`
مستندات: [راهنمای نودها](https://docs.sovereign-ai.local/nodes/)
`;
      render(<MarkdownContent content={markdown} />);

      const link = screen.getByRole("link", { name: "راهنمای نودها" });
      expect(link).toHaveAttribute("href", "https://docs.sovereign-ai.local/nodes/");
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
    });

    it("should display the actual source name for citations instead of numbered [1] and trigger click callback", () => {
      const markdown = "برای مطالعه بیشتر به [1] مراجعه کنید.";
      const citations: Citation[] = [
        {
          claimIndex: 0,
          title: "مستندات نودهای کلاستر",
          url: "https://docs.sovereign-ai.local/nodes",
          supportStatus: "supported",
        },
      ];
      const onCitationClick = vi.fn();

      render(
        <MarkdownContent
          content={markdown}
          citations={citations}
          onCitationClick={onCitationClick}
        />
      );

      // Verify that the title is displayed instead of [1]
      expect(screen.queryByText("[1]")).not.toBeInTheDocument();
      const citationLink = screen.getByRole("link", { name: /مستندات نودهای کلاستر/i });
      expect(citationLink).toBeInTheDocument();
      expect(citationLink).toHaveAttribute("href", "https://docs.sovereign-ai.local/nodes");

      fireEvent.click(citationLink);
      expect(onCitationClick).toHaveBeenCalledWith(citations[0]);
    });

    it("should render formulas in an isolated LTR math surface", () => {
      const markdown = "فرمول: $x^2 + \\frac{1}{2}$\n\n$$\\rho \\mathbf{v} = \\nabla p$$";
      const { container } = render(<MarkdownContent content={markdown} />);

      const formulas = screen.getAllByRole("math");
      expect(formulas).toHaveLength(2);
      expect(formulas[0]).toHaveAttribute("dir", "ltr");
      expect(formulas[0]).toHaveClass("math-inline");
      expect(formulas[1]).toHaveClass("math-display");
      expect(container.querySelector(".math-fraction")).toBeInTheDocument();
      expect(container.querySelector("p")).toHaveAttribute("dir", "auto");
    });

    it("should syntax-color fenced code while preserving LTR code direction", () => {
      const markdown = "```python\ndef deploy():\n    return True\n```";
      const { container } = render(<MarkdownContent content={markdown} />);

      const codeContainer = screen.getByRole("region", { name: /code snippet/i });
      expect(codeContainer).toHaveAttribute("dir", "ltr");
      expect(codeContainer.querySelector(".text-sky-300")).toBeInTheDocument();
      expect(container.querySelector("code")).toHaveTextContent("def deploy():");
    });
  });

  describe("Thread answer actions", () => {
    it("should copy the complete assistant answer", async () => {
      const writeTextMock = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: {
          writeText: writeTextMock,
        },
      });
      Object.defineProperty(HTMLElement.prototype, "scrollTo", {
        configurable: true,
        value: vi.fn(),
      });

      const message: MessageType = {
        id: "assistant-1",
        role: "assistant",
        content: "پاسخ **کامل** با فرمول $x^2$",
        status: "complete",
        createdAt: new Date().toISOString(),
      };

      render(<Thread messages={[message]} language="fa" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: "کپی پاسخ" }));
      });

      expect(writeTextMock).toHaveBeenCalledWith(message.content);
    });
  });

  describe("Composer Component", () => {
    it("should submit on Enter and insert newline on Shift+Enter", () => {
      const onSubmit = vi.fn();
      render(<Composer onSubmit={onSubmit} isStreaming={false} language="fa" />);

      const textarea = screen.getByPlaceholderText(/از دستیار هوشمند بپرسید/i);

      // Shift+Enter should not submit
      fireEvent.change(textarea, { target: { value: "خط اول" } });
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });
      expect(onSubmit).not.toHaveBeenCalled();

      // Enter without shift should submit
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
      expect(onSubmit).toHaveBeenCalledWith("خط اول");
    });

    it("should display cancel button while streaming", () => {
      const onCancel = vi.fn();
      render(<Composer onSubmit={vi.fn()} onCancel={onCancel} isStreaming={true} language="fa" />);

      const cancelBtn = screen.getByRole("button", { name: /توقف پاسخ/i });
      expect(cancelBtn).toBeInTheDocument();
      fireEvent.click(cancelBtn);
      expect(onCancel).toHaveBeenCalled();
    });

    it("should display submit button and handle submission", () => {
      const onSubmit = vi.fn();
      render(<Composer onSubmit={onSubmit} isStreaming={false} language="fa" />);

      const textarea = screen.getByPlaceholderText(/از دستیار هوشمند بپرسید/i);
      fireEvent.change(textarea, { target: { value: "پرسش جدید" } });

      const sendBtn = screen.getByRole("button", { name: /ارسال پیام/i });
      expect(sendBtn).toBeInTheDocument();
      fireEvent.click(sendBtn);
      expect(onSubmit).toHaveBeenCalledWith("پرسش جدید");
    });

    it("should handle drag and drop of PDF files into the composer", async () => {
      const onUploadPdf = vi.fn().mockResolvedValue({
        id: "att-1",
        name: "document.pdf",
        size: 1024 * 100,
        type: "pdf",
      });

      render(
        <Composer
          onSubmit={vi.fn()}
          onUploadPdf={onUploadPdf}
          language="fa"
        />
      );

      const textarea = screen.getByPlaceholderText(/از دستیار هوشمند بپرسید/i);
      const fakePdfFile = new File(["%PDF-1.4 test"], "document.pdf", { type: "application/pdf" });

      await act(async () => {
        fireEvent.dragEnter(textarea, {
          dataTransfer: {
            items: [{ kind: "file", type: "application/pdf" }],
          },
        });
      });

      await act(async () => {
        fireEvent.drop(textarea, {
          dataTransfer: {
            files: [fakePdfFile],
          },
        });
      });

      expect(onUploadPdf).toHaveBeenCalledWith(fakePdfFile);
    });
  });

  describe("WorkflowProgress Component", () => {
    it("should render workflow stages with polite live announcements", () => {
      const workflow: Workflow = {
        id: "wf-1",
        type: "troubleshooting",
        goal: "بررسی خطای پورت در FastAPI",
        state: "checking",
        stepCount: 2,
        nextAction: "بررسی مقدار PORT در محیط",
      };

      render(<WorkflowProgress workflow={workflow} stage="verifying" label="در حال بررسی تنظیمات پورت…" language="fa" />);

      const liveRegion = screen.getByRole("status");
      expect(liveRegion).toHaveAttribute("aria-live", "polite");
      expect(screen.getByText(/در حال بررسی تنظیمات پورت…/i)).toBeInTheDocument();
      expect(screen.getByText(/بررسی مقدار PORT در محیط/i)).toBeInTheDocument();
    });
  });

  describe("SourceCard Component", () => {
    it("should render official source details, section, and verification status without numbered badges", () => {
      const citation: Citation = {
        claimIndex: 0,
        title: "راه‌اندازی برنامه‌های FastAPI",
        section: "تنظیم پورت و متغیرها",
        url: "https://docs.sovereign-ai.local/paas/python/fastapi",
        supportStatus: "supported",
      };

      render(<SourceCard citation={citation} language="fa" />);

      expect(screen.getByText("راه‌اندازی برنامه‌های FastAPI")).toBeInTheDocument();
      expect(screen.getByText("تنظیم پورت و متغیرها")).toBeInTheDocument();
      expect(screen.getByText(/مستندات پایگاه دانش/i)).toBeInTheDocument();
      expect(screen.getByText(/مستندات رسمی/i)).toBeInTheDocument();
      expect(screen.queryByText("[1]")).not.toBeInTheDocument();
    });
  });

  describe("AccountPanel Component Policy Compliance", () => {
    it("should render modular settings tabs and prohibited controls must not be present", async () => {
      render(<AccountPanel isOpen={true} onClose={vi.fn()} language="fa" onLanguageChange={vi.fn()} />);

      expect(screen.getByText(/تنظیمات عمومی/i)).toBeInTheDocument();
      expect(screen.getByText(/گوینده صوتی/i)).toBeInTheDocument();
      expect(screen.getByText(/سهمیه و مصرف/i)).toBeInTheDocument();
      expect(screen.getByText(/کلیدهای MCP/i)).toBeInTheDocument();
      expect(screen.getAllByText(/حساب کاربری/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/مستندات API/i)).toBeInTheDocument();

      // Prohibited controls check:
      expect(screen.queryByRole("button", { name: /ثبت نام|signup|sign up/i })).not.toBeInTheDocument();
      expect(screen.queryByText(/همگام‌سازی|sync/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/تم روشن|light mode/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/انتخاب مدل|model selector/i)).not.toBeInTheDocument();
    });

    it("should render platform specifications in general tab", () => {
      render(<AccountPanel isOpen={true} onClose={vi.fn()} language="fa" onLanguageChange={vi.fn()} />);

      expect(screen.getByText(/مشخصات نگارش و پلتفرم/i)).toBeInTheDocument();
      expect(screen.getByText(/Sovereign Control Plane v2\.0/i)).toBeInTheDocument();
      expect(screen.getByText(/LiteLLM \+ vLLM CUDA 12/i)).toBeInTheDocument();
    });
  });

  describe("EmptyChat Component", () => {
    it("should render starter actions and headline", () => {
      const onSelectStarter = vi.fn();
      render(<EmptyChat onSelectStarter={onSelectStarter} language="fa" />);

      expect(screen.getByText(/چطور می‌توانم کمکتان کنم؟/i)).toBeInTheDocument();
      expect(screen.getByText(/یافتن مستندات کلاستر/i)).toBeInTheDocument();
      expect(screen.getByText(/بررسی سلامت نودها و شبکه/i)).toBeInTheDocument();
      expect(screen.getByText(/مسیریابی هوشمند و RAG/i)).toBeInTheDocument();
    });
  });
});
